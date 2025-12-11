import React from 'react';
import { TrendingUp } from 'lucide-react';

interface HeaderProps {
  scrolled: boolean;
  onLoginClick?: () => void;
}

export default function Header({ scrolled, onLoginClick }: HeaderProps) {
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    element?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <header 
      className={`fixed top-0 w-full z-50 transition-all duration-300 ${
        scrolled 
          ? 'bg-white/95 backdrop-blur-lg shadow-lg' 
          : 'bg-white/80 backdrop-blur-sm'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="w-11 h-11 bg-gradient-to-br from-blue-600 to-blue-500 rounded-xl flex items-center justify-center shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <span 
              style={{ fontFamily: 'Crimson Pro, serif' }} 
              className="text-2xl font-bold text-gray-900"
            >
              SME PULSE
            </span>
          </div>
          
          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            <button 
              onClick={() => scrollToSection('gioi-thieu')}
              className="text-gray-600 hover:text-blue-600 transition-colors font-semibold text-[20px]"
            >
              Giới thiệu
            </button>
            <button 
              onClick={() => scrollToSection('tinh-nang')}
              className="text-gray-600 hover:text-blue-600 transition-colors font-semibold text-[20px]"
            >
              Tính năng
            </button>
            <button 
              onClick={() => scrollToSection('lien-he')}
              className="text-gray-600 hover:text-blue-600 transition-colors font-semibold text-[20px]"
            >
              Liên hệ
            </button>
          </nav>

          {/* Login Button */}
          <button 
            onClick={onLoginClick}
            className="bg-gradient-to-r from-blue-600 to-blue-500 text-white px-[20px] py-[8px] rounded-lg font-semibold hover:shadow-lg hover:scale-105 transition-all duration-200 text-[18px]"
          >
            Đăng nhập
          </button>
        </div>
      </div>
    </header>
  );
}
