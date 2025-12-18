"""Excel export service for generating reports"""

import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from app.core.config import settings

logger = logging.getLogger(__name__)

class ExcelExportService:
    """Service for generating formatted Excel reports"""
    
    def __init__(self):
        """Initialize Excel export service"""
        # Create temp directory if not exists
        self.temp_dir = Path(settings.EXPORT_TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def export_ar_aging(self, df: pd.DataFrame, org_id: int) -> str:
        """
        Export AR aging report to Excel
        
        Args:
            df: DataFrame with AR aging data
            org_id: Organization ID
            
        Returns:
            Local file path
        """
        try:
            # Create filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"ar_aging_{org_id}_{timestamp}.xlsx"
            file_path = self.temp_dir / filename
            
            # Create Excel workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "AR Aging"
            
            # Add title
            ws["A1"] = "BÁO CÁO NỢ KHÁCH (AR AGING)"
            ws["A1"].font = Font(size=14, bold=True)
            ws.merge_cells("A1:F1")
            
            # Add date
            ws["A2"] = f"Ngày: {datetime.utcnow().strftime('%d/%m/%Y')}"
            ws["A2"].font = Font(size=10)
            ws.merge_cells("A2:F2")
            
            # Add data with formatting
            self._add_dataframe_to_sheet(ws, df, start_row=4)
            
            # Adjust column widths
            ws.column_dimensions["A"].width = 15
            ws.column_dimensions["B"].width = 15
            ws.column_dimensions["C"].width = 15
            ws.column_dimensions["D"].width = 12
            ws.column_dimensions["E"].width = 12
            
            # Save workbook
            wb.save(file_path)
            logger.info(f"✅ Generated AR Aging report: {file_path}")
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to export AR aging: {e}")
            raise
    
    def export_ap_aging(self, df: pd.DataFrame, org_id: int) -> str:
        """
        Export AP aging report to Excel
        
        Args:
            df: DataFrame with AP aging data
            org_id: Organization ID
            
        Returns:
            Local file path
        """
        try:
            # Create filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"ap_aging_{org_id}_{timestamp}.xlsx"
            file_path = self.temp_dir / filename
            
            # Create Excel workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "AP Aging"
            
            # Add title
            ws["A1"] = "BÁO CÁO NỢ NHÀ CUNG CẤP (AP AGING)"
            ws["A1"].font = Font(size=14, bold=True)
            ws.merge_cells("A1:F1")
            
            # Add date
            ws["A2"] = f"Ngày: {datetime.utcnow().strftime('%d/%m/%Y')}"
            ws["A2"].font = Font(size=10)
            ws.merge_cells("A2:F2")
            
            # Add data with formatting
            self._add_dataframe_to_sheet(ws, df, start_row=4)
            
            # Adjust column widths
            ws.column_dimensions["A"].width = 15
            ws.column_dimensions["B"].width = 15
            ws.column_dimensions["C"].width = 15
            ws.column_dimensions["D"].width = 12
            ws.column_dimensions["E"].width = 12
            
            # Save workbook
            wb.save(file_path)
            logger.info(f"✅ Generated AP Aging report: {file_path}")
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to export AP aging: {e}")
            raise
    
    def export_cashflow_forecast(self, df: pd.DataFrame, org_id: int) -> str:
        """
        Export cashflow forecast to Excel
        
        Args:
            df: DataFrame with forecast data
            org_id: Organization ID
            
        Returns:
            Local file path
        """
        try:
            # Create filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"cashflow_forecast_{org_id}_{timestamp}.xlsx"
            file_path = self.temp_dir / filename
            
            # Create Excel workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Cashflow Forecast"
            
            # Add title
            ws["A1"] = "DỰ BÁO DÒNG TIỀN (CASHFLOW FORECAST)"
            ws["A1"].font = Font(size=14, bold=True)
            ws.merge_cells("A1:D1")
            
            # Add date
            ws["A2"] = f"Ngày: {datetime.utcnow().strftime('%d/%m/%Y')}"
            ws["A2"].font = Font(size=10)
            ws.merge_cells("A2:D2")
            
            # Add data with formatting
            self._add_dataframe_to_sheet(ws, df, start_row=4)
            
            # Adjust column widths
            ws.column_dimensions["A"].width = 12
            ws.column_dimensions["B"].width = 18
            ws.column_dimensions["C"].width = 18
            
            # Save workbook
            wb.save(file_path)
            logger.info(f"✅ Generated Cashflow Forecast report: {file_path}")
            
            return str(file_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to export cashflow forecast: {e}")
            raise
    
    def _add_dataframe_to_sheet(self, ws, df: pd.DataFrame, start_row: int = 1):
        """
        Add DataFrame to worksheet with formatting
        
        Args:
            ws: Worksheet object
            df: DataFrame to add
            start_row: Starting row number
        """
        # Remove timezone from datetime columns (Excel doesn't support timezones)
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None) if df[col].dt.tz is not None else df[col]
            elif df[col].dtype == 'object':
                # Check for datetime objects with timezone in object columns
                try:
                    df[col] = pd.to_datetime(df[col], errors='ignore')
                    if hasattr(df[col].dt, 'tz') and df[col].dt.tz is not None:
                        df[col] = df[col].dt.tz_localize(None)
                except:
                    pass
        
        # Header styling
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )
        
        # Add headers
        for col_idx, col_name in enumerate(df.columns, 1):
            cell = ws.cell(row=start_row, column=col_idx)
            cell.value = col_name
            cell.fill = header_fill
            cell.font = header_font
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Add data rows
        for row_idx, row in enumerate(dataframe_to_rows(df, index=False, header=False), start_row + 1):
            for col_idx, value in enumerate(row, 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.value = value
                cell.border = border
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
                # Format numbers with thousands separator
                if isinstance(value, (int, float)):
                    cell.number_format = "#,##0.00"
                    cell.alignment = Alignment(horizontal="right", vertical="center")


# Singleton instance
excel_service = ExcelExportService()
