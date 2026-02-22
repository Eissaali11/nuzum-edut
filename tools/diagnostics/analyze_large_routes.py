#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Routes File Splitter - تقسيم ملفات الروت الكبيرة

يقوم بتحليل ملفات الروت الكبيرة (>300 سطر) وتقسيمها إلى وحدات منفصلة
لتحسين صيانة الكود وقابلية القراءة والأداء.

الاستخدام:
    python split_routes.py
    python split_routes.py --analyze-only
"""

import os
import sys
import ast
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple
import re

@dataclass
class RouteInfo:
    """معلومات عن الروت"""
    name: str  # اسم الدالة
    line_start: int  # رقم السطر البداية
    line_end: int  # رقم السطر النهاية
    lines: int  # عدد الأسطر
    decorator: str  # مثلاً @bp.route('/path')
    
    def __str__(self):
        return f"{self.name} ({self.lines} سطر، من {self.line_start} إلى {self.line_end})"

@dataclass
class HelperFunction:
    """معلومات عن دالة مساعدة"""
    name: str
    line_start: int
    line_end: int
    lines: int
    
    def __str__(self):
        return f"{self.name} ({self.lines} سطر)"

class RouteAnalyzer:
    """محلل ملفات الروت"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_name = self.file_path.name
        self.lines = self._read_file()
        self.routes: List[RouteInfo] = []
        self.helpers: List[HelperFunction] = []
        self.imports: str = ""
        self.blueprint_name: str = None
        
    def _read_file(self) -> List[str]:
        """قراءة ملف Python"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return f.readlines()
    
    def analyze(self):
        """تحليل الملف وتحديد الروتات والدوال المساعدة"""
        import_lines = []
        route_decorators = {}
        current_line = 0
        
        # استخراج الاستيرادات والتعريفات
        for i, line in enumerate(self.lines, 1):
            stripped = line.strip()
            
            # استخراج استيرادات
            if i < 100 and (stripped.startswith('import ') or stripped.startswith('from ')):
                import_lines.append(i)
            
            # البحث عن اسم Blueprint
            if 'Blueprint(' in stripped and not self.blueprint_name:
                match = re.search(r"([a-z_]+)\s*=\s*Blueprint\(", line)
                if match:
                    self.blueprint_name = match.group(1)
            
            # تتبع decorators الروتات
            if '@' in line and 'route' in line:
                route_decorators[i] = line.strip()
        
        # استخراج كود الاستيرادات
        if import_lines:
            self.imports = "".join(self.lines[:import_lines[-1]])
        
        # تحليل الدوال باستخدام AST
        try:
            tree = ast.parse("".join(self.lines))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    line_start = node.lineno
                    line_end = node.end_lineno if node.end_lineno else line_start
                    lines_count = line_end - line_start + 1
                    
                    # التحقق من وجود decorator للروت
                    is_route = False
                    decorator = None
                    for dec_line, dec_text in route_decorators.items():
                        if dec_line == line_start - 1:
                            is_route = True
                            decorator = dec_text
                            break
                    
                    if is_route:
                        self.routes.append(RouteInfo(
                            name=node.name,
                            line_start=line_start,
                            line_end=line_end,
                            lines=lines_count,
                            decorator=decorator
                        ))
                    elif lines_count > 50:  # دوال مساعدة كبيرة
                        self.helpers.append(HelperFunction(
                            name=node.name,
                            line_start=line_start,
                            line_end=line_end,
                            lines=lines_count
                        ))
        except SyntaxError as e:
            print(f"⚠️ خطأ في تحليل {self.file_name}: {e}")
    
    def get_summary(self) -> Dict:
        """الحصول على ملخص التحليل"""
        total_lines = len(self.lines)
        large_routes = [r for r in self.routes if r.lines > 100]
        
        return {
            'file': self.file_name,
            'total_lines': total_lines,
            'routes_count': len(self.routes),
            'helpers_count': len(self.helpers),
            'large_routes': large_routes,
            'blueprint_name': self.blueprint_name
        }
    
    def print_analysis(self):
        """طباعة نتائج التحليل"""
        summary = self.get_summary()
        
        print(f"\n{'='*70}")
        print(f"📄 {self.file_name}".center(70))
        print(f"{'='*70}")
        print(f"📊 إحصائيات الملف:")
        print(f"   • إجمالي الأسطر: {summary['total_lines']}")
        print(f"   • عدد الروتات: {summary['routes_count']}")
        print(f"   • عدد الدوال المساعدة: {summary['helpers_count']}")
        print(f"   • اسم Blueprint: {summary['blueprint_name'] or 'غير محدد'}")
        
        if summary['large_routes']:
            print(f"\n⚠️  روتات كبيرة الحجم ({len(summary['large_routes'])} روت):")
            for route in sorted(summary['large_routes'], key=lambda r: r.lines, reverse=True):
                print(f"   • {route} ⚠️")
        
        if self.helpers:
            print(f"\n🔧 دوال مساعدة كبيرة ({len(self.helpers)} دالة):")
            for helper in sorted(self.helpers, key=lambda h: h.lines, reverse=True)[:5]:
                print(f"   • {helper}")
    
    def suggest_split(self) -> Dict[str, List[RouteInfo]]:
        """اقتراح كيفية تقسيم الملف"""
        if len(self.routes) <= 3:
            return {}
        
        # تجميع الروتات حسب نمط الـ URL
        groups = defaultdict(list)
        
        for route in self.routes:
            # استخراج الجزء الأول من المسار
            if route.decorator:
                match = re.search(r"route\(['\"]([^/']+)", route.decorator)
                if match:
                    prefix = match.group(1)
                else:
                    prefix = 'general'
            else:
                prefix = 'general'
            
            groups[prefix].append(route)
        
        # إرجاع المجموعات التي تحتوي على أكثر من روت واحد
        return {k: v for k, v in groups.items() if len(v) > 1}

class ProjectAnalyzer:
    """محلل المشروع الكامل"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.routes_dir = self.project_path / 'routes'
        self.files_analysis = []
    
    def analyze_all_routes(self):
        """تحليل جميع ملفات الروت"""
        if not self.routes_dir.exists():
            print(f"❌ لم يتم العثور على مجلد routes في {self.project_path}")
            return
        
        print("\n" + "="*70)
        print("📈 تحليل ملفات الروت الكبيرة في المشروع".center(70))
        print("="*70)
        
        large_files = []
        
        for py_file in self.routes_dir.glob('*.py'):
            analyzer = RouteAnalyzer(str(py_file))
            analyzer.analyze()
            
            summary = analyzer.get_summary()
            
            if summary['total_lines'] > 300:
                large_files.append((py_file.name, summary['total_lines']))
                analyzer.print_analysis()
                self.files_analysis.append((py_file, analyzer))
        
        # ملخص الملفات الكبيرة
        print("\n" + "="*70)
        print("📊 ملخص الملفات الكبيرة (>300 سطر)".center(70))
        print("="*70)
        
        if large_files:
            for file_name, lines in sorted(large_files, key=lambda x: x[1], reverse=True):
                status = "🔴" if lines > 600 else "🟡"
                print(f"{status} {file_name}: {lines} سطر")
        else:
            print("✅ لا توجد ملفات كبيرة")
        
        # إرجاع الملفات المرشحة للتقسيم
        candidates = [f for f, lines in large_files if lines > 500]
        return candidates
    
    def print_recommendations(self):
        """طباعة التوصيات"""
        print("\n" + "="*70)
        print("💡 التوصيات".center(70))
        print("="*70)
        
        for py_file, analyzer in self.files_analysis:
            summary = analyzer.get_summary()
            
            if summary['total_lines'] > 300:
                print(f"\n📄 {py_file.name}:")
                print(f"   • عدد الروتات: {summary['routes_count']}")
                
                splits = analyzer.suggest_split()
                if splits:
                    print(f"   • اقتراح بتقسيم الملف إلى {len(splits)} وحدات:")
                    for group_name, routes in splits.items():
                        print(f"     - {group_name}_routes.py ({len(routes)} روت)")
                else:
                    print(f"   ✅ لا يوجد اقتراح بالتقسيم (ملف محدود العدد)")

def main():
    """البرنامج الرئيسي"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='تحليل وتقسيم ملفات الروت الكبيرة',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--project-path',
        default='d:\\nuzm',
        help='مسار المشروع (افتراضي: d:\\nuzm)'
    )
    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='فقط تحليل بدون تقسيم'
    )
    
    args = parser.parse_args()
    
    analyzer = ProjectAnalyzer(args.project_path)
    candidates = analyzer.analyze_all_routes()
    analyzer.print_recommendations()
    
    print("\n" + "="*70)
    print("✅ انتهى التحليل".center(70))
    print("="*70)
    
    if candidates:
        print(f"\n📌 ملفات مرشحة للتقسيم ({len(candidates)}):")
        for file_name in candidates:
            print(f"   • {file_name}")
        print("\n💡 لتقسيم الملفات يدوياً:")
        print("   1. استخدم الروتات المقترحة")
        print("   2. انسخ الروتات ذات الصلة إلى ملفات جديدة")
        print("   3. أضف الاستيرادات اللازمة")
        print("   4. سجل الـ blueprints الجديدة في app.py")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
