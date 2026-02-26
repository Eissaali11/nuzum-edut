"""
معالج البيانات والاستخراج
==========================
استخراج البيانات من قاعدة البيانات وتنسيقها للتقارير
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import pandas as pd


class DataSource(ABC):
    """واجهة مصادر البيانات"""
    
    @abstractmethod
    def get_data(self) -> pd.DataFrame:
        """استخراج البيانات"""
        pass
    
    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """الحصول على ملخص البيانات"""
        pass


class DataProcessor:
    """معالج البيانات والحسابات"""
    
    @staticmethod
    def calculate_totals(data: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, float]:
        """حساب المجاميع"""
        totals = {}
        for col in numeric_cols:
            if col in data.columns:
                totals[col] = data[col].sum()
        return totals
    
    @staticmethod
    def calculate_averages(data: pd.DataFrame, numeric_cols: List[str]) -> Dict[str, float]:
        """حساب المتوسطات"""
        averages = {}
        for col in numeric_cols:
            if col in data.columns:
                averages[col] = data[col].mean()
        return averages
    
    @staticmethod
    def calculate_percentage(value: float, total: float) -> float:
        """حساب النسبة المئوية"""
        return (value / total * 100) if total > 0 else 0
    
    @staticmethod
    def filter_by_date_range(data: pd.DataFrame, 
                           date_column: str,
                           start_date: datetime,
                           end_date: datetime) -> pd.DataFrame:
        """تصفية البيانات حسب نطاق التاريخ"""
        mask = (data[date_column] >= start_date) & (data[date_column] <= end_date)
        return data[mask]
    
    @staticmethod
    def group_and_sum(data: pd.DataFrame,
                     group_columns: List[str],
                     sum_columns: List[str]) -> pd.DataFrame:
        """تجميع البيانات والجمع"""
        return data.groupby(group_columns)[sum_columns].sum().reset_index()
    
    @staticmethod
    def sort_by_value(data: pd.DataFrame,
                     column: str,
                     ascending: bool = False) -> pd.DataFrame:
        """ترتيب البيانات حسب قيمة"""
        return data.sort_values(by=column, ascending=ascending)
    
    @staticmethod
    def get_top_n(data: pd.DataFrame,
                  column: str,
                  n: int = 10,
                  ascending: bool = False) -> pd.DataFrame:
        """الحصول على أعلى n صفوف"""
        return data.sort_values(by=column, ascending=ascending).head(n)


class DataExtractor:
    """استخراج البيانات من مصادر مختلفة"""
    
    def __init__(self):
        """تهيئة المستخرج"""
        self.processor = DataProcessor()
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """استخراج مقاييس لوحة القيادة"""
        try:
            from src.app import db
            from src.application.models.statistics import Statistics
            from datetime import datetime as dt, timedelta
            
            # البيانات الإحصائية الأساسية
            total_records = db.session.query(Statistics).count()
            today_records = db.session.query(Statistics)\
                .filter_by(created_date=dt.now().date()).count()
            
            # حساب معدل النمو
            yesterday = dt.now().date() - timedelta(days=1)
            yesterday_records = db.session.query(Statistics)\
                .filter_by(created_date=yesterday).count()
            
            growth_rate = self.processor.calculate_percentage(
                today_records - yesterday_records,
                yesterday_records
            ) if yesterday_records > 0 else 0
            
            return {
                'total_records': total_records,
                'today_records': today_records,
                'growth_rate': growth_rate,
                'yesterday_records': yesterday_records,
                'generated_date': dt.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            # البيانات الافتراضية عند الخطأ
            return {
                'total_records': 0,
                'today_records': 0,
                'growth_rate': 0,
                'yesterday_records': 0,
                'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def get_category_distribution(self) -> pd.DataFrame:
        """استخراج توزيع الفئات"""
        try:
            from src.app import db
            from sqlalchemy import func
            
            # بيانات وهمية احترافية للتطوير
            data = {
                'الفئة': ['إدارة التسليم', 'الجودة', 'الأداء', 'السلامة', 'أخرى'],
                'العدد': [45, 28, 35, 22, 15],
                'النسبة': [28.5, 17.7, 22.2, 13.9, 9.5]
            }
            return pd.DataFrame(data)
        except Exception as e:
            # بيانات افتراضية
            return pd.DataFrame({
                'الفئة': ['افتراضي'],
                'العدد': [0],
                'النسبة': [0]
            })
    
    def get_monthly_trends(self) -> pd.DataFrame:
        """استخراج اتجاهات شهرية"""
        try:
            months = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو']
            data = {
                'الشهر': months,
                'المبيعات': [15000, 18000, 22000, 19000, 25000, 28000],
                'التكاليف': [8000, 9500, 11000, 10500, 12000, 13500],
                'الأرباح': [7000, 8500, 11000, 8500, 13000, 14500]
            }
            return pd.DataFrame(data)
        except Exception as e:
            return pd.DataFrame()
    
    def get_performance_data(self) -> pd.DataFrame:
        """استخراج بيانات الأداء"""
        try:
            data = {
                'الوحدة': ['الوحدة الأولى', 'الوحدة الثانية', 'الوحدة الثالثة', 
                          'الوحدة الرابعة', 'الوحدة الخامسة'],
                'الهدف': [100, 95, 110, 105, 90],
                'المنجز': [98, 92, 115, 103, 88],
                'النسبة': [98.0, 96.8, 104.5, 98.1, 97.8],
                'الحالة': ['ممتاز', 'جيد جداً', 'ممتاز', 'جيد جداً', 'جيد جداً']
            }
            return pd.DataFrame(data)
        except Exception as e:
            return pd.DataFrame()
    
    def get_top_performers(self, limit: int = 10) -> pd.DataFrame:
        """استخراج الأفضل أداءً"""
        try:
            data = {
                'الترتيب': list(range(1, limit + 1)),
                'الاسم': [f'الموظف {i}' for i in range(1, limit + 1)],
                'الأداء': [95 - i*2 for i in range(limit)],
                'المبيعات': [50000 - i*2000 for i in range(limit)],
                'التقييم': ['⭐⭐⭐⭐⭐' if i < 3 else '⭐⭐⭐⭐' for i in range(limit)]
            }
            return pd.DataFrame(data)
        except Exception as e:
            return pd.DataFrame()
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """استخراج الإحصائيات العامة"""
        metrics = self.get_dashboard_metrics()
        
        return {
            'title': 'التقرير الشامل',
            'period': 'شهري',
            'currency': 'ريال سعودي',
            'metrics': metrics,
            'report_date': datetime.now().strftime('%d/%m/%Y'),
            'report_time': datetime.now().strftime('%H:%M:%S')
        }
