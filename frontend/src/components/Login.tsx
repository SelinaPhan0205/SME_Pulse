import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, User, KeyRound, ArrowRight, TrendingUp } from 'lucide-react';
import { motion } from 'framer-motion';
import { useLogin } from '../lib/api/hooks';
import { toast } from 'sonner';

export default function Login() {
  const navigate = useNavigate();
  const loginMutation = useLogin();
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    remember: false
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    console.log('=== LOGIN ATTEMPT ===');
    console.log('Email:', formData.email);
    console.log('Password length:', formData.password.length);
    
    try {
      // ✅ Call real backend API
      console.log('Calling loginMutation.mutateAsync...');
      const result = await loginMutation.mutateAsync({
        email: formData.email,
        password: formData.password,
      });
      
      console.log('Login success!', result);
      toast.success('Đăng nhập thành công!');
      navigate('/dashboard');
    } catch (error: any) {
      console.error('=== LOGIN ERROR ===');
      console.error('Error object:', error);
      console.error('Response:', error.response);
      console.error('Response data:', error.response?.data);
      console.error('Status:', error.response?.status);
      
      const errorMessage = error.response?.data?.detail || error.message || 'Đăng nhập thất bại';
      console.error('Error message:', errorMessage);
      toast.error(errorMessage);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  return (
    <div className="relative w-full min-h-screen bg-white">
      {/* Header - Compact & Clean */}
      <header className="relative z-50 bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
          {/* Logo */}
          <div 
            className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity" 
            onClick={() => navigate('/')}
          >
            <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-blue-500 rounded-lg flex items-center justify-center shadow-md">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <span 
              style={{ fontFamily: 'Crimson Pro, serif' }} 
              className="text-xl font-bold text-gray-900"
            >
              SME PULSE
            </span>
          </div>

          {/* Navigation & Back Button - Grouped Right */}
          <div className="flex items-center gap-8">
            <nav className="hidden md:flex items-center gap-8">
              <button 
                onClick={() => navigate('/')} 
                className="text-[20px] text-gray-600 hover:text-blue-600 transition-colors font-semibold"
              >
                Giới thiệu
              </button>
              <button 
                onClick={() => navigate('/')} 
                className="text-[20px] text-gray-600 hover:text-blue-600 transition-colors font-semibold"
              >
                Tính năng
              </button>
              <button 
                onClick={() => navigate('/')} 
                className="text-[20px] text-gray-600 hover:text-blue-600 transition-colors font-semibold"
              >
                Liên hệ
              </button>
            </nav>

            {/* Back Button */}
            <button 
              onClick={() => navigate('/')}
              className="bg-gradient-to-r from-blue-600 to-blue-500 text-white px-[20px] py-[8px] rounded-lg text-[20px] font-semibold hover:shadow-lg hover:scale-105 transition-all duration-200 pt-[3px] pr-[20px] pb-[8px] pl-[20px]"
            >
              Quay lại
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex min-h-[calc(100vh-60px)]">
        {/* Left Side - Video Background */}
        <div className="relative w-1/2 overflow-hidden bg-gradient-to-br from-blue-900 to-blue-700">
          {/* Video Layer */}
          <video 
            autoPlay 
            loop 
            muted 
            playsInline
            className="absolute inset-0 w-full h-full object-cover opacity-50"
          >
            <source src="https://cdn.pixabay.com/video/2024/11/01/237596_large.mp4" type="video/mp4" />
            Trình duyệt của bạn không hỗ trợ video.
          </video>
          
          {/* Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-br from-blue-900/80 to-blue-700/80" />

          {/* Text Content - Centered */}
          <div className="relative z-10 h-full flex items-center justify-center px-12 py-16">
            <motion.div 
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8 }}
              className="max-w-xl text-center"
            >
              <h1 className="font-['Darker_Grotesque'] font-extrabold text-5xl leading-tight text-white mb-6">
                SME Pulse
                <br />
                Hệ Thống Quản Lý
                <br />
                Dòng Tiền
              </h1>
              <p className="font-['Darker_Grotesque'] text-xl text-white/95 leading-relaxed mb-8">
                Giải pháp tài chính thông minh cho doanh nghiệp
              </p>
              
              {/* Feature Pills */}
              <div className="flex flex-wrap justify-center gap-3">
                <div className="bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-white text-sm font-['Darker_Grotesque']">
                  ✓ Dự báo dòng tiền AI
                </div>
                <div className="bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-white text-sm font-['Darker_Grotesque']">
                  ✓ Quản lý công nợ
                </div>
                <div className="bg-white/20 backdrop-blur-sm px-4 py-2 rounded-full text-white text-sm font-['Darker_Grotesque']">
                  ✓ Tích hợp VietQR
                </div>
              </div>
            </motion.div>
          </div>
        </div>

        {/* Right Side - Login Form - Centered Vertically */}
        <div className="w-1/2 flex items-center justify-center bg-gray-50 px-8 py-16">
          <motion.div 
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="w-full max-w-md"
          >
            {/* Logo and Title */}
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-600 to-blue-500 rounded-2xl mb-4 shadow-lg">
                <Building2 className="w-8 h-8 text-white" strokeWidth={2} />
              </div>
              <h2 className="text-3xl font-['Darker_Grotesque'] font-bold text-gray-900 mb-2">
                Chào Mừng Trở Lại
              </h2>
              <p className="font-['Darker_Grotesque'] text-gray-600">
                Đăng nhập vào tài khoản của bạn
              </p>
            </div>

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Email Field */}
              <div>
                <label className="block text-sm font-['Darker_Grotesque'] font-semibold text-gray-700 mb-2">
                  Email
                </label>
                <div className="relative">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="admin@sme.com"
                    className="w-full pl-12 pr-4 py-3 bg-white border-2 border-gray-200 rounded-xl font-['Darker_Grotesque'] placeholder:text-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                    required
                  />
                </div>
              </div>

              {/* Password Field */}
              <div>
                <label className="block text-sm font-['Darker_Grotesque'] font-semibold text-gray-700 mb-2">
                  Mật khẩu
                </label>
                <div className="relative">
                  <KeyRound className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="Nhập mật khẩu..."
                    className="w-full pl-12 pr-4 py-3 bg-white border-2 border-gray-200 rounded-xl font-['Darker_Grotesque'] placeholder:text-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all"
                    required
                  />
                </div>
              </div>

              {/* Remember & Forgot */}
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    name="remember"
                    checked={formData.remember}
                    onChange={handleChange}
                    className="w-4 h-4 border-2 border-gray-300 rounded accent-blue-600 cursor-pointer"
                  />
                  <span className="text-sm font-['Darker_Grotesque'] text-gray-700 group-hover:text-gray-900">
                    Ghi nhớ đăng nhập
                  </span>
                </label>
                <a href="#" className="text-sm font-['Darker_Grotesque'] font-semibold text-blue-600 hover:text-blue-700 hover:underline">
                  Quên mật khẩu?
                </a>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="w-full bg-gradient-to-r from-blue-600 to-blue-500 text-white py-3 rounded-xl shadow-lg font-['Darker_Grotesque'] font-semibold flex items-center justify-center gap-2 hover:shadow-xl hover:scale-[1.02] transition-all group mt-6"
              >
                Đăng nhập
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </button>
            </form>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
