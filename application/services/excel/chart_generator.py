"""
مولد الرسوم البيانية الاحترافية
==============================
إنشاء رسوم بيانية احترافية تفاعلية
"""

from typing import Dict, List, Any, Optional
from openpyxl.chart import (
    PieChart, PieChart3D, BarChart, LineChart, DoughnutChart,
    Reference, Series
)
from openpyxl.drawing.image import Image as XLImage
from openpyxl.chart.label import DataLabelList
import pandas as pd


class ChartConfig:
    """إعدادات الرسوم البيانية"""
    
    # الألوان الاحترافية للرسوم البيانية
    COLORS = [
        '0D1117',  # أزرق بحري
        '00D4AA',  # أخضر زمردي
        '00D4FF',  # سماوي
        'FFD700',  # ذهب
        '4CAF50',  # أخضر
        'FF6B6B',  # أحمر
        '9C27B0',  # بنفسجي
        'FF9800',  # برتقالي
    ]
    
    DEFAULT_WIDTH = 15  # عرض الرسم البياني (سم)
    DEFAULT_HEIGHT = 10  # ارتفاع الرسم البياني (سم)
    DEFAULT_STYLE = 10  # نمط الرسم البياني


class ChartGenerator:
    """منشئ الرسوم البيانية"""
    
    def __init__(self):
        """تهيئة منشئ الرسوم البيانية"""
        self.config = ChartConfig()
    
    def create_pie_chart(self,
                        data: pd.DataFrame,
                        category_column: str,
                        value_column: str,
                        title: str = 'رسم بياني دائري',
                        sheet=None,
                        position: str = 'A1') -> Optional[PieChart]:
        """
        إنشاء رسم بياني دائري احترافي
        
        Args:
            data: بيانات التقرير
            category_column: عمود الفئات
            value_column: عمود القيم
            title: عنوان الرسم
            sheet: ورقة العمل
            position: موضع الرسم
        """
        try:
            if sheet is None or data.empty:
                return None
            
            # إنشاء الرسم البياني
            chart = PieChart3D()
            chart.title = title
            chart.style = self.config.DEFAULT_STYLE
            
            # تنسيق العنوان
            chart.title.tx.rich.p[0].pPr = None
            
            # إضافة البيانات
            ref = Reference(sheet, min_col=1, min_row=2, max_row=len(data) + 1)
            chart.add_data(ref, titles_from_data=False)
            
            # تنسيق إضافي
            chart.height = self.config.DEFAULT_HEIGHT / 2.54
            chart.width = self.config.DEFAULT_WIDTH / 2.54
            
            # إضافة الشكيات
            chart.dataLabels = DataLabelList()
            chart.dataLabels.showVal = True
            chart.dataLabels.showPercent = True
            chart.dataLabels.showCatName = True
            
            return chart
        except Exception as e:
            print(f"خطأ في إنشاء الرسم الدائري: {e}")
            return None
    
    def create_bar_chart(self,
                        data: pd.DataFrame,
                        category_column: str,
                        value_columns: List[str],
                        title: str = 'رسم بياني عمودي',
                        sheet=None,
                        position: str = 'A1') -> Optional[BarChart]:
        """
        إنشاء رسم بياني عمودي احترافي
        
        Args:
            data: بيانات التقرير
            category_column: عمود الفئات
            value_columns: أعمدة القيم
            title: عنوان الرسم
            sheet: ورقة العمل
            position: موضع الرسم
        """
        try:
            if sheet is None or data.empty:
                return None
            
            # إنشاء الرسم البياني
            chart = BarChart()
            chart.type = "col"  # عمودي
            chart.style = self.config.DEFAULT_STYLE
            chart.title = title
            chart.y_axis.title = 'القيمة'
            chart.x_axis.title = 'الفئة'
            
            # تنسيق الألوان
            for idx, color in enumerate(self.config.COLORS[:len(value_columns)]):
                series = Series(chart.series[idx] if idx < len(chart.series) else None)
                # يتم تطبيق الألوان من خلال النمط
            
            # تنسيق إضافي
            chart.height = self.config.DEFAULT_HEIGHT / 2.54
            chart.width = self.config.DEFAULT_WIDTH / 2.54
            
            # إضافة البيانات
            chart.dataLabels = DataLabelList()
            chart.dataLabels.showVal = True
            
            return chart
        except Exception as e:
            print(f"خطأ في إنشاء الرسم العمودي: {e}")
            return None
    
    def create_line_chart(self,
                         data: pd.DataFrame,
                         x_column: str,
                         y_columns: List[str],
                         title: str = 'رسم بياني خطي',
                         sheet=None,
                         position: str = 'A1') -> Optional[LineChart]:
        """
        إنشاء رسم بياني خطي احترافي
        
        Args:
            data: بيانات التقرير
            x_column: عمود المحور الأفقي
            y_columns: أعمدة المحور الرأسي
            title: عنوان الرسم
            sheet: ورقة العمل
            position: موضع الرسم
        """
        try:
            if sheet is None or data.empty:
                return None
            
            # إنشاء الرسم البياني
            chart = LineChart()
            chart.title = title
            chart.style = self.config.DEFAULT_STYLE
            chart.y_axis.title = 'القيمة'
            chart.x_axis.title = x_column
            
            # تنسيق إضافي
            chart.height = self.config.DEFAULT_HEIGHT / 2.54
            chart.width = self.config.DEFAULT_WIDTH / 2.54
            
            # تفعيل الشبكة
            chart.y_axis.delete = False
            
            return chart
        except Exception as e:
            print(f"خطأ في إنشاء الرسم الخطي: {e}")
            return None
    
    def create_doughnut_chart(self,
                             data: pd.DataFrame,
                             category_column: str,
                             value_column: str,
                             title: str = 'رسم بياني دائري',
                             sheet=None,
                             position: str = 'A1') -> Optional[DoughnutChart]:
        """
        إنشاء رسم بياني دائري مفرغ
        
        Args:
            data: بيانات التقرير
            category_column: عمود الفئات
            value_column: عمود القيم
            title: عنوان الرسم
            sheet: ورقة العمل
            position: موضع الرسم
        """
        try:
            if sheet is None or data.empty:
                return None
            
            # إنشاء الرسم البياني
            chart = DoughnutChart()
            chart.title = title
            chart.style = self.config.DEFAULT_STYLE
            
            # تنسيق إضافي
            chart.height = self.config.DEFAULT_HEIGHT / 2.54
            chart.width = self.config.DEFAULT_WIDTH / 2.54
            
            # إضافة الشكيات
            chart.dataLabels = DataLabelList()
            chart.dataLabels.showVal = True
            chart.dataLabels.showPercent = True
            
            return chart
        except Exception as e:
            print(f"خطأ في إنشاء الرسم المفرغ: {e}")
            return None
    
    @staticmethod
    def apply_chart_colors(chart, colors: List[str]) -> None:
        """
        تطبيق الألوان على الرسم البياني
        
        Args:
            chart: الرسم البياني
            colors: قائمة الألوان بصيغة HEX
        """
        try:
            if hasattr(chart, 'series'):
                for idx, series in enumerate(chart.series):
                    if idx < len(colors):
                        if hasattr(series, 'dPt'):
                            for point in series.dPt:
                                point.graphicalProperties.solidFill = colors[idx]
        except Exception as e:
            print(f"خطأ في تطبيق الألوان: {e}")
    
    @staticmethod
    def add_chart_to_sheet(sheet,
                          chart,
                          position: str = 'A1') -> None:
        """
        إضافة الرسم البياني إلى الورقة
        
        Args:
            sheet: ورقة العمل
            chart: الرسم البياني
            position: موضع الإضافة
        """
        try:
            if chart is not None and sheet is not None:
                sheet.add_chart(chart, position)
        except Exception as e:
            print(f"خطأ في إضافة الرسم: {e}")
