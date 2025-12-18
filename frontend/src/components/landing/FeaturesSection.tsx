import React from 'react';
import { motion } from 'framer-motion';
import { Link2, TrendingUp, Bell, RefreshCw, Store, Shield } from 'lucide-react';

const features = [
  {
    icon: Link2,
    title: "Tích hợp một chạm",
    desc: "Kết nối với POS, bảng tính và ngân hàng."
  },
  {
    icon: TrendingUp,
    title: "Dòng tiền thời gian thực",
    desc: "Theo dõi dòng vào và dòng ra từng ngày."
  },
  {
    icon: Bell,
    title: "Cảnh báo thông minh",
    desc: "Nhận thông báo về bất thường và hóa đơn chậm."
  },
  {
    icon: RefreshCw,
    title: "Đối soát tự động",
    desc: "Khớp giao dịch và giảm công việc thủ công."
  },
  {
    icon: Store,
    title: "Hỗ trợ đa cửa hàng",
    desc: "Tổng hợp tất cả chi nhánh vào một bảng điều khiển."
  },
  {
    icon: Shield,
    title: "Bảo mật cấp ngân hàng",
    desc: "Mã hóa khi lưu trữ và truyền tải."
  }
];

export default function FeaturesSection() {
  return (
    <section id="tinh-nang" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16 space-y-4"
        >
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900">
            Mọi thứ bạn cần, không gì thừa
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            SME Pulse mang đến sự rõ ràng về tài chính để vận hành doanh nghiệp với tự tin.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: idx * 0.1 }}
              className="group bg-gradient-to-br from-slate-50 to-blue-50 p-8 rounded-2xl hover:shadow-xl transition-all duration-300 hover:-translate-y-2"
            >
              <div className="w-16 h-16 bg-gradient-to-br from-blue-600 to-blue-500 rounded-xl flex items-center justify-center text-white mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg">
                <feature.icon className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
              <p className="text-gray-600 leading-relaxed">{feature.desc}</p>
            </motion.div>
          ))}
        </div>

        {/* How it Works */}
        <motion.div
          initial={{ opacity: 0, y: 50 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="mt-24"
        >
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-4xl sm:text-5xl font-bold text-gray-900">
              Cách hoạt động
            </h2>
            <p className="text-xl text-gray-600">
              Khởi chạy và vận hành chỉ trong vài phút.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-12 lg:gap-16 relative">
            {/* Connecting lines - fixed position */}
            <div className="hidden md:block absolute top-12 left-[16.666%] w-[33.333%] h-0.5 bg-gradient-to-r from-blue-500 to-blue-400 pointer-events-none z-0"></div>
            <div className="hidden md:block absolute top-12 left-[50%] w-[33.333%] h-0.5 bg-gradient-to-r from-blue-500 to-blue-400 pointer-events-none z-0"></div>
            
            {[
              { num: "1", title: "Kết nối", desc: "Chọn công cụ và cấp quyền truy cập." },
              { num: "2", title: "Đồng bộ", desc: "Chúng tôi nhập và chuẩn hóa dữ liệu của bạn một cách bảo mật." },
              { num: "3", title: "Theo dõi", desc: "Bảng điều khiển và cảnh báo xuất hiện ngay lập tức." }
            ].map((step, idx) => (
              <div key={idx} className="relative text-center">
                <motion.div
                  whileHover={{ scale: 1.1 }}
                  transition={{ type: "spring", stiffness: 300 }}
                  className="relative inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-blue-600 to-blue-400 rounded-full text-white text-4xl font-bold mb-6 shadow-xl z-10"
                >
                  {step.num}
                </motion.div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4">{step.title}</h3>
                <p className="text-gray-600 leading-relaxed text-lg">{step.desc}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
