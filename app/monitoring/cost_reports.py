import json
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from app.monitoring.cost_dashboard import cost_dashboard
from app.monitoring.cost_tracker import cost_tracker
from app.logging.logger import Logger

logger = Logger()

class CostReports:
    """Generate and export cost reports in various formats."""
    
    def __init__(self):
        self.logger = logger
        self.dashboard = cost_dashboard
        self.tracker = cost_tracker
    
    def export_daily_costs_csv(self, output_file: str, days: int = 30) -> bool:
        """Export daily costs to CSV file."""
        try:
            daily_costs = self.dashboard.get_daily_costs(days)
            
            if not daily_costs:
                self.logger.warning("No daily cost data available for export")
                return False
            
            # Prepare CSV data
            fieldnames = ['date', 'llm_cost', 'llm_calls', 'ocr_cost', 'ocr_calls', 'total_cost']
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(daily_costs)
            
            self.logger.info(f"📊 Daily costs exported to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error exporting daily costs CSV: {str(e)}")
            return False
    
    def export_module_costs_csv(self, output_file: str, session_id: int = None, kramak_id: int = None) -> bool:
        """Export module cost breakdown to CSV file."""
        try:
            module_data = self.dashboard.get_module_costs(session_id, kramak_id)
            
            if not module_data or 'modules' not in module_data:
                self.logger.warning("No module cost data available for export")
                return False
            
            # Prepare CSV data
            csv_data = []
            for module_name, data in module_data['modules'].items():
                csv_data.append({
                    'module_name': module_name,
                    'total_cost': data['cost'],
                    'calls': data['calls'],
                    'tokens': data['tokens'],
                    'avg_response_time_ms': data['avg_response_time_ms'],
                    'cached_calls': data['cached_calls'],
                    'cache_hit_rate': data['cache_hit_rate'],
                    'cost_per_call': data['cost_per_call'],
                    'cost_per_token': data['cost_per_token']
                })
            
            fieldnames = ['module_name', 'total_cost', 'calls', 'tokens', 'avg_response_time_ms', 
                         'cached_calls', 'cache_hit_rate', 'cost_per_call', 'cost_per_token']
            
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)
            
            self.logger.info(f"📊 Module costs exported to: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error exporting module costs CSV: {str(e)}")
            return False
    
    def generate_monthly_report(self, month: int = None, year: int = None, output_dir: str = "reports") -> Dict:
        """Generate comprehensive monthly cost report."""
        try:
            # Default to current month if not specified
            if not month or not year:
                now = datetime.now()
                month = month or now.month
                year = year or now.year
            
            # Calculate date range for the month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            
            days_in_month = (end_date - start_date).days + 1
            
            # Get daily costs for the month
            daily_costs = self.dashboard.get_daily_costs(days_in_month)
            
            # Filter for the specific month
            month_costs = [
                d for d in daily_costs 
                if start_date.strftime('%Y-%m-%d') <= d['date'] <= end_date.strftime('%Y-%m-%d')
            ]
            
            # Calculate monthly totals
            total_monthly_cost = sum(d['total_cost'] for d in month_costs)
            total_llm_cost = sum(d['llm_cost'] for d in month_costs)
            total_ocr_cost = sum(d['ocr_cost'] for d in month_costs)
            total_llm_calls = sum(d['llm_calls'] for d in month_costs)
            total_ocr_calls = sum(d['ocr_calls'] for d in month_costs)
            
            # Get module breakdown
            module_costs = self.dashboard.get_module_costs()
            
            # Get cost trends
            trends = self.dashboard.get_cost_trends(days_in_month)
            
            monthly_report = {
                'report_info': {
                    'report_type': 'monthly_cost_report',
                    'month': month,
                    'year': year,
                    'generated_at': datetime.now().isoformat(),
                    'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                },
                'summary': {
                    'total_cost': round(total_monthly_cost, 4),
                    'llm_cost': round(total_llm_cost, 4),
                    'ocr_cost': round(total_ocr_cost, 4),
                    'total_calls': total_llm_calls + total_ocr_calls,
                    'llm_calls': total_llm_calls,
                    'ocr_calls': total_ocr_calls,
                    'avg_daily_cost': round(total_monthly_cost / len(month_costs), 4) if month_costs else 0,
                    'days_with_activity': len([d for d in month_costs if d['total_cost'] > 0])
                },
                'daily_breakdown': month_costs,
                'module_breakdown': module_costs,
                'trends': trends,
                'cost_analysis': {
                    'highest_cost_day': max(month_costs, key=lambda x: x['total_cost']) if month_costs else None,
                    'lowest_cost_day': min(month_costs, key=lambda x: x['total_cost']) if month_costs else None,
                    'llm_percentage': round((total_llm_cost / total_monthly_cost * 100), 2) if total_monthly_cost > 0 else 0,
                    'ocr_percentage': round((total_ocr_cost / total_monthly_cost * 100), 2) if total_monthly_cost > 0 else 0
                }
            }
            
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Export to JSON
            json_file = f"{output_dir}/monthly_report_{year}_{month:02d}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(monthly_report, f, indent=2, ensure_ascii=False)
            
            # Export daily costs to CSV
            csv_file = f"{output_dir}/daily_costs_{year}_{month:02d}.csv"
            self.export_daily_costs_csv(csv_file, days_in_month)
            
            # Export module costs to CSV
            module_csv_file = f"{output_dir}/module_costs_{year}_{month:02d}.csv"
            self.export_module_costs_csv(module_csv_file)
            
            self.logger.info(f"📊 Monthly report generated: {json_file}")
            self.logger.info(f"💰 Monthly total cost: ₹{total_monthly_cost:.4f}")
            
            return monthly_report
            
        except Exception as e:
            self.logger.error(f"❌ Error generating monthly report: {str(e)}")
            return {}
    
    def generate_kramak_cost_report(self, kramak_id: int, output_dir: str = "reports") -> Dict:
        """Generate detailed cost report for a specific kramak."""
        try:
            kramak_summary = self.dashboard.get_kramak_cost_summary(kramak_id)
            
            if not kramak_summary:
                self.logger.warning(f"No cost data found for kramak ID: {kramak_id}")
                return {}
            
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Export to JSON
            json_file = f"{output_dir}/kramak_{kramak_id}_cost_report.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(kramak_summary, f, indent=2, ensure_ascii=False)
            
            # Generate formatted text report
            text_file = f"{output_dir}/kramak_{kramak_id}_cost_report.txt"
            self._generate_text_report(kramak_summary, text_file)
            
            self.logger.info(f"📊 Kramak cost report generated: {json_file}")
            self.logger.info(f"💰 Kramak total cost: ₹{kramak_summary['costs']['total_cost']:.4f}")
            
            return kramak_summary
            
        except Exception as e:
            self.logger.error(f"❌ Error generating kramak cost report: {str(e)}")
            return {}
    
    def _generate_text_report(self, summary: Dict, output_file: str):
        """Generate a formatted text report."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"KRAMAK COST REPORT - ID: {summary['kramak_id']}\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("COST SUMMARY:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Cost:     ₹{summary['costs']['total_cost']:.4f}\n")
                f.write(f"LLM Cost:       ₹{summary['costs']['llm_cost']:.4f}\n")
                f.write(f"OCR Cost:       ₹{summary['costs']['ocr_cost']:.4f}\n\n")
                
                f.write("API CALLS:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Total Calls:    {summary['calls']['total_calls']}\n")
                f.write(f"LLM Calls:      {summary['calls']['llm_calls']}\n")
                f.write(f"OCR Calls:      {summary['calls']['ocr_calls']}\n")
                f.write(f"Cached Calls:   {summary['calls']['cached_calls']}\n")
                f.write(f"Cache Hit Rate: {summary['calls']['cache_hit_rate']:.1f}%\n\n")
                
                f.write("EFFICIENCY METRICS:\n")
                f.write("-" * 40 + "\n")
                f.write(f"Cost per Token:     ₹{summary['tokens']['cost_per_token']:.6f}\n")
                f.write(f"Cost per Character: ₹{summary['text_processing']['cost_per_character']:.6f}\n")
                f.write(f"Total Tokens:       {summary['tokens']['total_tokens']:,}\n")
                f.write(f"Total Characters:   {summary['text_processing']['total_characters_extracted']:,}\n\n")
                
                if 'modules' in summary['module_breakdown']:
                    f.write("MODULE BREAKDOWN:\n")
                    f.write("-" * 40 + "\n")
                    for module, data in summary['module_breakdown']['modules'].items():
                        f.write(f"{module:20} ₹{data['cost']:8.4f} ({data['calls']:3d} calls, {data['cache_hit_rate']:5.1f}% cached)\n")
                
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"Report generated at: {summary['timestamp']}\n")
                f.write("=" * 80 + "\n")
            
            self.logger.info(f"📄 Text report generated: {output_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Error generating text report: {str(e)}")

# Global cost reports instance
cost_reports = CostReports() 