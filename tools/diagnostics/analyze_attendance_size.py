#!/usr/bin/env python3
import re

with open(r'd:\nuzm\routes\attendance.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Find all route definitions
routes = re.finditer(r"@attendance_bp\.route\('([^']+)'\)", content)
route_lines = []

for match in routes:
    start_pos = match.start()
    # Count lines before this position
    start_line = content[:start_pos].count('\n') + 1
    route_name = match.group(1)
    route_lines.append((route_name, start_line))

# Add helper functions
route_lines.append(('format_time_12h_ar', 25))
route_lines.append(('format_time_12h_ar_short', 44))

# Add end position
route_lines.sort(key=lambda x: x[1])

# Calculate sizes
sizes = []
for i, (name, start) in enumerate(route_lines):
    if i < len(route_lines) - 1:
        end = route_lines[i + 1][1]
    else:
        end = len(lines)
    
    size = end - start
    sizes.append((name, start, end, size))

# Sort by size
sizes.sort(key=lambda x: x[3], reverse=True)

print("Top 20 Largest Functions:")
print("-" * 80)
print(f"{'Function':<40} {'Lines':>6} {'Start':>6} {'End':>6}")
print("-" * 80)
for name, start, end, size in sizes[:20]:
    print(f"{name:<40} {size:>6} {start:>6} {end:>6}")

print(f"\nTotal functions: {len(sizes)}")
print(f"Total lines in file: {len(lines)}")

# Calculate total lines from top 5 functions
top_5_sum = sum(size for _, _, _, size in sizes[:5])
print(f"\nTop 5 functions total lines: {top_5_sum} ({(top_5_sum/len(lines))*100:.1f}% of file)")
