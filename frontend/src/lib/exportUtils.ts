/**
 * Export utilities - Client-side export cho Reports
 * Export trực tiếp từ data hiện có trên frontend, không cần đợi backend
 */

import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface RevenueData {
  date: string;
  revenue: number;
}

interface PaymentData {
  method: string;
  success: number;
  failed: number;
  total: number;
  amount: number;
}

interface ARAgingData {
  range: string;
  amount: number;
  count: number;
}

interface ReconciliationData {
  date: string;
  reconciled: number;
  pending: number;
}

/**
 * Format số tiền VNĐ
 */
const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
};

/**
 * Export dữ liệu doanh thu ra XLSX
 */
export const exportRevenueXLSX = (data: RevenueData[], period: string) => {
  const wb = XLSX.utils.book_new();
  
  // Tạo sheet với header
  const wsData = [
    ['BÁO CÁO DOANH THU', '', ''],
    [`Kỳ báo cáo: ${period}`, '', ''],
    ['', '', ''],
    ['Ngày', 'Doanh thu (VNĐ)', 'Ghi chú'],
    ...data.map(d => [d.date, d.revenue, '']),
    ['', '', ''],
    ['TỔNG CỘNG', data.reduce((sum, d) => sum + d.revenue, 0), ''],
  ];
  
  const ws = XLSX.utils.aoa_to_sheet(wsData);
  
  // Set column widths
  ws['!cols'] = [{ wch: 15 }, { wch: 20 }, { wch: 20 }];
  
  XLSX.utils.book_append_sheet(wb, ws, 'Doanh thu');
  XLSX.writeFile(wb, `BaoCao_DoanhThu_${period.replace(/\//g, '-')}.xlsx`);
};

/**
 * Export dữ liệu thanh toán ra XLSX
 */
export const exportPaymentXLSX = (data: PaymentData[], period: string) => {
  const wb = XLSX.utils.book_new();
  
  const wsData = [
    ['BÁO CÁO THANH TOÁN', '', '', '', ''],
    [`Kỳ báo cáo: ${period}`, '', '', '', ''],
    ['', '', '', '', ''],
    ['Phương thức', 'Thành công', 'Thất bại', 'Tổng GD', 'Số tiền (VNĐ)'],
    ...data.map(d => [d.method, d.success, d.failed, d.total, d.amount]),
    ['', '', '', '', ''],
    ['TỔNG CỘNG', 
      data.reduce((sum, d) => sum + d.success, 0),
      data.reduce((sum, d) => sum + d.failed, 0),
      data.reduce((sum, d) => sum + d.total, 0),
      data.reduce((sum, d) => sum + d.amount, 0)
    ],
  ];
  
  const ws = XLSX.utils.aoa_to_sheet(wsData);
  ws['!cols'] = [{ wch: 15 }, { wch: 12 }, { wch: 12 }, { wch: 12 }, { wch: 20 }];
  
  XLSX.utils.book_append_sheet(wb, ws, 'Thanh toán');
  XLSX.writeFile(wb, `BaoCao_ThanhToan_${period.replace(/\//g, '-')}.xlsx`);
};

/**
 * Export dữ liệu công nợ ra XLSX
 */
export const exportARAgingXLSX = (data: ARAgingData[], period: string) => {
  const wb = XLSX.utils.book_new();
  
  const wsData = [
    ['BÁO CÁO CÔNG NỢ PHẢI THU', '', ''],
    [`Kỳ báo cáo: ${period}`, '', ''],
    ['', '', ''],
    ['Tuổi nợ', 'Số tiền (VNĐ)', 'Số hóa đơn'],
    ...data.map(d => [d.range, d.amount, d.count]),
    ['', '', ''],
    ['TỔNG CỘNG', data.reduce((sum, d) => sum + d.amount, 0), data.reduce((sum, d) => sum + d.count, 0)],
  ];
  
  const ws = XLSX.utils.aoa_to_sheet(wsData);
  ws['!cols'] = [{ wch: 15 }, { wch: 20 }, { wch: 12 }];
  
  XLSX.utils.book_append_sheet(wb, ws, 'Công nợ');
  XLSX.writeFile(wb, `BaoCao_CongNo_${period.replace(/\//g, '-')}.xlsx`);
};

/**
 * Export dữ liệu đối soát ra XLSX
 */
export const exportReconciliationXLSX = (data: ReconciliationData[], period: string) => {
  const wb = XLSX.utils.book_new();
  
  const wsData = [
    ['BÁO CÁO ĐỐI SOÁT', '', ''],
    [`Kỳ báo cáo: ${period}`, '', ''],
    ['', '', ''],
    ['Ngày', 'Đã đối soát (VNĐ)', 'Chờ xử lý (VNĐ)'],
    ...data.map(d => [d.date, d.reconciled, d.pending]),
    ['', '', ''],
    ['TỔNG CỘNG', 
      data.reduce((sum, d) => sum + d.reconciled, 0),
      data.reduce((sum, d) => sum + d.pending, 0)
    ],
  ];
  
  const ws = XLSX.utils.aoa_to_sheet(wsData);
  ws['!cols'] = [{ wch: 15 }, { wch: 20 }, { wch: 20 }];
  
  XLSX.utils.book_append_sheet(wb, ws, 'Đối soát');
  XLSX.writeFile(wb, `BaoCao_DoiSoat_${period.replace(/\//g, '-')}.xlsx`);
};

// ============== PDF EXPORTS ==============

/**
 * Export dữ liệu doanh thu ra PDF
 */
export const exportRevenuePDF = (data: RevenueData[], period: string) => {
  const doc = new jsPDF();
  
  // Title
  doc.setFontSize(18);
  doc.text('BAO CAO DOANH THU', 105, 20, { align: 'center' });
  
  doc.setFontSize(12);
  doc.text(`Ky bao cao: ${period}`, 105, 30, { align: 'center' });
  
  // Table
  autoTable(doc, {
    startY: 40,
    head: [['Ngay', 'Doanh thu (VND)']],
    body: data.map(d => [d.date, formatCurrency(d.revenue)]),
    foot: [['TONG CONG', formatCurrency(data.reduce((sum, d) => sum + d.revenue, 0))]],
    styles: { fontSize: 10 },
    headStyles: { fillColor: [59, 130, 246] },
    footStyles: { fillColor: [241, 245, 249], textColor: [0, 0, 0], fontStyle: 'bold' },
  });
  
  doc.save(`BaoCao_DoanhThu_${period.replace(/\//g, '-')}.pdf`);
};

/**
 * Export dữ liệu thanh toán ra PDF
 */
export const exportPaymentPDF = (data: PaymentData[], period: string) => {
  const doc = new jsPDF();
  
  doc.setFontSize(18);
  doc.text('BAO CAO THANH TOAN', 105, 20, { align: 'center' });
  
  doc.setFontSize(12);
  doc.text(`Ky bao cao: ${period}`, 105, 30, { align: 'center' });
  
  autoTable(doc, {
    startY: 40,
    head: [['Phuong thuc', 'Thanh cong', 'That bai', 'Tong GD', 'So tien (VND)']],
    body: data.map(d => [d.method, d.success, d.failed, d.total, formatCurrency(d.amount)]),
    foot: [[
      'TONG CONG',
      data.reduce((sum, d) => sum + d.success, 0),
      data.reduce((sum, d) => sum + d.failed, 0),
      data.reduce((sum, d) => sum + d.total, 0),
      formatCurrency(data.reduce((sum, d) => sum + d.amount, 0))
    ]],
    styles: { fontSize: 9 },
    headStyles: { fillColor: [59, 130, 246] },
    footStyles: { fillColor: [241, 245, 249], textColor: [0, 0, 0], fontStyle: 'bold' },
  });
  
  doc.save(`BaoCao_ThanhToan_${period.replace(/\//g, '-')}.pdf`);
};

/**
 * Export dữ liệu công nợ ra PDF
 */
export const exportARAgingPDF = (data: ARAgingData[], period: string) => {
  const doc = new jsPDF();
  
  doc.setFontSize(18);
  doc.text('BAO CAO CONG NO PHAI THU', 105, 20, { align: 'center' });
  
  doc.setFontSize(12);
  doc.text(`Ky bao cao: ${period}`, 105, 30, { align: 'center' });
  
  autoTable(doc, {
    startY: 40,
    head: [['Tuoi no', 'So tien (VND)', 'So hoa don']],
    body: data.map(d => [d.range, formatCurrency(d.amount), d.count]),
    foot: [[
      'TONG CONG',
      formatCurrency(data.reduce((sum, d) => sum + d.amount, 0)),
      data.reduce((sum, d) => sum + d.count, 0)
    ]],
    styles: { fontSize: 10 },
    headStyles: { fillColor: [59, 130, 246] },
    footStyles: { fillColor: [241, 245, 249], textColor: [0, 0, 0], fontStyle: 'bold' },
  });
  
  doc.save(`BaoCao_CongNo_${period.replace(/\//g, '-')}.pdf`);
};

/**
 * Export dữ liệu đối soát ra PDF
 */
export const exportReconciliationPDF = (data: ReconciliationData[], period: string) => {
  const doc = new jsPDF();
  
  doc.setFontSize(18);
  doc.text('BAO CAO DOI SOAT', 105, 20, { align: 'center' });
  
  doc.setFontSize(12);
  doc.text(`Ky bao cao: ${period}`, 105, 30, { align: 'center' });
  
  autoTable(doc, {
    startY: 40,
    head: [['Ngay', 'Da doi soat (VND)', 'Cho xu ly (VND)']],
    body: data.map(d => [d.date, formatCurrency(d.reconciled), formatCurrency(d.pending)]),
    foot: [[
      'TONG CONG',
      formatCurrency(data.reduce((sum, d) => sum + d.reconciled, 0)),
      formatCurrency(data.reduce((sum, d) => sum + d.pending, 0))
    ]],
    styles: { fontSize: 10 },
    headStyles: { fillColor: [59, 130, 246] },
    footStyles: { fillColor: [241, 245, 249], textColor: [0, 0, 0], fontStyle: 'bold' },
  });
  
  doc.save(`BaoCao_DoiSoat_${period.replace(/\//g, '-')}.pdf`);
};
