from datetime import date as _date, datetime as _datetime, timedelta as _timedelta
from ..models.attendance_queries import AttendanceQuery


class AttendanceService:
    @staticmethod
    def get_processed_dashboard_data(project_name=None):
        today = _datetime.now().date()
        current_month = today.month
        current_year = today.year
        start_of_month = today.replace(day=1)
        last_day = __import__('calendar').monthrange(current_year, current_month)[1]

        # Data access
        employee_subq = AttendanceQuery.build_employee_subquery(project_name)
        rows = AttendanceQuery.get_aggregate_rows(start_of_month, today, employee_subq)

        # Build map date -> status -> count
        from collections import defaultdict
        map_by_date = defaultdict(lambda: {'present': 0, 'absent': 0, 'leave': 0, 'sick': 0})
        for r in rows:
            map_by_date[r.att_date]['%s' % r.att_status] = int(r.cnt)

        # Prepare daily_attendance_data for charting (1..last_day)
        daily_attendance_data = []
        for day in range(1, last_day + 1):
            current_date = _date(current_year, current_month, day)
            if current_date > today:
                break
            stats = map_by_date.get(current_date, {'present': 0, 'absent': 0, 'leave': 0, 'sick': 0})
            daily_attendance_data.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'day': str(day),
                'present': stats.get('present', 0),
                'absent': stats.get('absent', 0)
            })

        # Range stats
        daily_stats = AttendanceQuery.range_stats(today, today, employee_subq)
        weekly_start = start_of_month + _timedelta(days=((today.day - 1) // 7) * 7)
        weekly_end = min(start_of_month + _timedelta(days=((today.day - 1) // 7) * 7 + 6), _date(current_year, current_month, last_day))
        weekly_stats = AttendanceQuery.range_stats(weekly_start, weekly_end, employee_subq)
        monthly_stats = AttendanceQuery.range_stats(start_of_month, today, employee_subq)

        def stats_to_dict(stats_data):
            result = {'present': 0, 'absent': 0, 'leave': 0, 'sick': 0, 'late': 0}
            for item in stats_data:
                result[item[0]] = int(item[1])
            return result

        daily_stats_dict = stats_to_dict(daily_stats)
        weekly_stats_dict = stats_to_dict(weekly_stats)
        monthly_stats_dict = stats_to_dict(monthly_stats)

        # Compute 'late' counts for today based on attendance rows and grace period
        try:
            attendance_rows = AttendanceQuery.get_attendance_rows_for_date(today, employee_subq)
            late_count = 0
            for row in attendance_rows:
                try:
                    # prefer fields named check_in_time and shift_start_time
                    check_in = getattr(row, 'check_in_time', None) or getattr(row, 'time_in', None)
                    shift_start = getattr(row, 'shift_start_time', None) or getattr(row, 'shift_time', None)
                    minutes_late = AttendanceService.calculate_late_minutes(check_in, shift_start, grace_period=15)
                    if minutes_late > 0:
                        late_count += 1
                except Exception:
                    continue
            daily_stats_dict['late'] = late_count
        except Exception:
            daily_stats_dict['late'] = daily_stats_dict.get('late', 0)

        # Chart payloads
        daily_chart_data = {
            'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
            'datasets': [{
                'data': [daily_stats_dict['present'], daily_stats_dict['absent'], daily_stats_dict['leave'], daily_stats_dict['sick']],
                'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
            }]
        }

        weekly_chart_data = {
            'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
            'datasets': [{
                'data': [weekly_stats_dict['present'], weekly_stats_dict['absent'], weekly_stats_dict['leave'], weekly_stats_dict['sick']],
                'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
            }]
        }

        monthly_chart_data = {
            'labels': ['حاضر', 'غائب', 'إجازة', 'مرضي'],
            'datasets': [{
                'data': [monthly_stats_dict['present'], monthly_stats_dict['absent'], monthly_stats_dict['leave'], monthly_stats_dict['sick']],
                'backgroundColor': ['#28a745', '#dc3545', '#ffc107', '#17a2b8']
            }]
        }

        daily_trend_chart_data = {
            'labels': [item['day'] for item in daily_attendance_data],
            'datasets': [
                {'label': 'الحضور', 'data': [item['present'] for item in daily_attendance_data]},
                {'label': 'الغياب', 'data': [item['absent'] for item in daily_attendance_data]},
                {'label': 'متأخرون', 'data': [item.get('late', 0) for item in daily_attendance_data]}
            ]
        }

        active_projects = AttendanceQuery.get_active_projects()
        active_employees_count = AttendanceQuery.active_employees_count(employee_subq)

        # summaries via AttendanceAnalytics if available
        daily_summary = None
        monthly_summary = None
        try:
            from src.services.attendance_analytics import AttendanceAnalytics
            daily_summary = AttendanceAnalytics.get_department_summary(start_date=today, end_date=today, project_name=project_name)
            monthly_summary = AttendanceAnalytics.get_department_summary(start_date=start_of_month, end_date=today, project_name=project_name)
        except Exception:
            pass

        return {
            'today': today,
            'current_month': current_month,
            'current_year': current_year,
            'current_month_name': ['يناير','فبراير','مارس','إبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'][current_month-1],
            'formatted_today': {'gregorian': today.strftime('%Y-%m-%d'), 'hijri': ''},
            'start_of_month': start_of_month,
            'end_of_month': _date(current_year, current_month, last_day),
            'start_of_week': start_of_month,
            'end_of_week': min(start_of_month + _timedelta(days=6), _date(current_year, current_month, last_day)),
            'daily_stats': daily_stats_dict,
            'weekly_stats': weekly_stats_dict,
            'monthly_stats': monthly_stats_dict,
            'daily_chart_data': daily_chart_data,
            'weekly_chart_data': weekly_chart_data,
            'monthly_chart_data': monthly_chart_data,
            'daily_trend_chart_data': daily_trend_chart_data,
            'daily_attendance_data': daily_attendance_data,
            'daily_summary': daily_summary,
            'monthly_summary': monthly_summary,
            'active_employees_count': active_employees_count,
            'active_projects': active_projects,
            'selected_project': project_name,
            'daily_attendance_rate': 0,
            'weekly_attendance_rate': 0,
            'monthly_attendance_rate': 0,
        }

    @staticmethod
    def calculate_late_minutes(check_in_time, shift_start_time, grace_period=15):
        # Delegate to v1 service logic implementation
        try:
            from .attendance_logic import calculate_late_minutes as _calc
            return _calc(check_in_time, shift_start_time, grace_period=grace_period)
        except Exception:
            return 0
