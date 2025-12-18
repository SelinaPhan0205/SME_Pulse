import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Phone, MapPin, Send, CheckCircle } from 'lucide-react';

export default function ContactSection() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    message: ''
  });

  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => {
      setSubmitted(false);
      setFormData({ name: '', email: '', phone: '', company: '', message: '' });
    }, 3000);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <section id="lien-he" className="py-24 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-blue-900 via-blue-800 to-blue-900 relative overflow-hidden">
      {/* Background Effects */}
      <div className="absolute inset-0 opacity-5">
        {[...Array(30)].map((_, i) => (
          <motion.div
            key={i}
            animate={{
              y: [0, -30, 0],
              opacity: [0.2, 0.5, 0.2],
            }}
            transition={{
              duration: 3 + Math.random() * 2,
              repeat: Infinity,
              delay: Math.random() * 2,
            }}
            className="absolute w-2 h-2 bg-white rounded-full"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
            }}
          />
        ))}
      </div>

      <div className="max-w-7xl mx-auto relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16 space-y-4"
        >
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight drop-shadow-lg">
            Sẵn sàng bắt đầu?
          </h2>
          <p className="text-xl text-gray-100 max-w-3xl mx-auto drop-shadow-md">
            Liên hệ với chúng tôi để được tư vấn và trải nghiệm SME Pulse miễn phí
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Contact Info */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="space-y-8"
          >
            <div className="bg-white/15 backdrop-blur-lg rounded-2xl p-8 border border-white/30 shadow-2xl">
              <h3 className="text-2xl font-bold text-white mb-6 drop-shadow-md">Thông tin liên hệ</h3>
              <div className="space-y-6">
                {[
                  { icon: Mail, text: 'contact@smepulse.vn', label: 'Email' },
                  { icon: Phone, text: '(+84) 123 456 789', label: 'Điện thoại' },
                  { icon: MapPin, text: 'Hà Nội, Việt Nam', label: 'Địa chỉ' },
                ].map((item, index) => (
                  <motion.div
                    key={index}
                    whileHover={{ x: 10 }}
                    className="flex items-start gap-4 group"
                  >
                    <div className="w-12 h-12 bg-white/25 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:bg-white/40 transition-all duration-300">
                      <item.icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <div className="text-gray-200 text-sm mb-1 font-medium">{item.label}</div>
                      <div className="text-white font-semibold">{item.text}</div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            <div className="bg-white/15 backdrop-blur-lg rounded-2xl p-8 border border-white/30 shadow-2xl">
              <h3 className="text-2xl font-bold text-white mb-4 drop-shadow-md">Tại sao chọn SME Pulse?</h3>
              <ul className="space-y-4">
                {[
                  'Tích hợp AI tiên tiến cho dự báo chính xác',
                  'Tùy biến hoàn toàn cho thị trường Việt Nam',
                  'Hỗ trợ VietQR và thanh toán số',
                  'Giao diện tiếng Việt thân thiện',
                  'Bảo mật dữ liệu cấp ngân hàng',
                  'Hỗ trợ khách hàng 24/7'
                ].map((item, idx) => (
                  <motion.li
                    key={idx}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: idx * 0.1 }}
                    className="flex items-center gap-3 text-gray-100 font-medium"
                  >
                    <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                    {item}
                  </motion.li>
                ))}
              </ul>
            </div>
          </motion.div>

          {/* Contact Form */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
          >
            <form onSubmit={handleSubmit} className="bg-white/15 backdrop-blur-lg rounded-2xl p-8 border border-white/30 shadow-2xl space-y-6">
              {submitted ? (
                <motion.div
                  initial={{ scale: 0.8, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className="text-center py-12"
                >
                  <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
                  <h3 className="text-2xl font-bold text-white mb-2 drop-shadow-md">Cảm ơn bạn!</h3>
                  <p className="text-gray-100 font-medium">Chúng tôi sẽ liên hệ với bạn sớm nhất có thể.</p>
                </motion.div>
              ) : (
                <>
                  <div>
                    <label className="block text-white text-sm font-semibold mb-2 drop-shadow">
                      Họ và tên <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleChange}
                      required
                      className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-xl focus:outline-none focus:border-white/50 focus:bg-white/25 transition-colors text-white placeholder-gray-300 font-medium"
                      placeholder="Nguyễn Văn A"
                    />
                  </div>

                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-white text-sm font-semibold mb-2 drop-shadow">
                        Email <span className="text-red-400">*</span>
                      </label>
                      <input
                        type="email"
                        name="email"
                        value={formData.email}
                        onChange={handleChange}
                        required
                        className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-xl focus:outline-none focus:border-white/50 focus:bg-white/25 transition-colors text-white placeholder-gray-300 font-medium"
                        placeholder="email@example.com"
                      />
                    </div>

                    <div>
                      <label className="block text-white text-sm font-semibold mb-2 drop-shadow">
                        Số điện thoại
                      </label>
                      <input
                        type="tel"
                        name="phone"
                        value={formData.phone}
                        onChange={handleChange}
                        className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-xl focus:outline-none focus:border-white/50 focus:bg-white/25 transition-colors text-white placeholder-gray-300 font-medium"
                        placeholder="0123456789"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-white text-sm font-semibold mb-2 drop-shadow">
                      Tên công ty
                    </label>
                    <input
                      type="text"
                      name="company"
                      value={formData.company}
                      onChange={handleChange}
                      className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-xl focus:outline-none focus:border-white/50 focus:bg-white/25 transition-colors text-white placeholder-gray-300 font-medium"
                      placeholder="Công ty TNHH ABC"
                    />
                  </div>

                  <div>
                    <label className="block text-white text-sm font-semibold mb-2 drop-shadow">
                      Tin nhắn
                    </label>
                    <textarea
                      name="message"
                      value={formData.message}
                      onChange={handleChange}
                      rows={4}
                      className="w-full px-4 py-3 bg-white/20 border border-white/30 rounded-xl focus:outline-none focus:border-white/50 focus:bg-white/25 transition-colors resize-none text-white placeholder-gray-300 font-medium"
                      placeholder="Để lại lời nhắn của bạn..."
                    />
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    type="submit"
                    className="w-full px-8 py-4 bg-white text-blue-600 rounded-xl font-bold text-lg hover:shadow-2xl transition-all duration-300 flex items-center justify-center gap-2"
                  >
                    Gửi tin nhắn
                    <Send className="w-5 h-5" />
                  </motion.button>
                </>
              )}
            </form>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
