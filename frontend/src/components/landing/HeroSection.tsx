import React from 'react';
import { motion } from 'framer-motion';
import { Play } from 'lucide-react';
import { ImageWithFallback } from '../figma/ImageWithFallback';

export default function HeroSection() {
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    element?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section id="gioi-thieu" className="pt-28 pb-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left Content */}
          <motion.div 
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8 }}
            className="space-y-8"
          >
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold text-gray-900 leading-tight">
              Làm rõ tài chính{' '}
              <span className="text-blue-600">cửa hàng</span>{' '}
              của bạn.
            </h1>
            
            <p className="text-xl text-gray-600 leading-relaxed max-w-xl">
              SME Pulse tập trung doanh thu, chi phí và dòng tiền vào một bảng điều khiển duy nhất.
            </p>

            <div className="flex flex-col sm:flex-row gap-4">
              <button 
                onClick={() => scrollToSection('lien-he')}
                className="bg-gradient-to-r from-blue-600 to-blue-500 text-white px-8 py-4 rounded-xl font-semibold text-lg hover:shadow-xl hover:scale-105 transition-all duration-200"
              >
                Dùng thử ngay
              </button>
              <button className="bg-white text-gray-700 px-8 py-4 rounded-xl font-semibold text-lg border-2 border-gray-200 hover:border-blue-500 hover:text-blue-600 transition-all duration-200 flex items-center justify-center gap-2">
                <Play className="w-5 h-5" />
                Xem demo trực tiếp
              </button>
            </div>


          </motion.div>

          {/* Right Image */}
          <motion.div 
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="relative"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-blue-400 to-cyan-300 rounded-3xl blur-3xl opacity-20"></div>
            <div className="relative bg-slate-900 rounded-2xl shadow-2xl overflow-hidden">
              <ImageWithFallback 
                src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1200&h=800&fit=crop&q=80" 
                alt="Dashboard Analytics" 
                className="w-full h-auto"
              />
            </div>
          </motion.div>
        </div>
      </div>

      {/* Logo Cloud */}
      <div className="pt-32 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="relative overflow-hidden">
            <motion.div 
              className="flex items-center gap-12"
              animate={{
                x: [0, -1400],
              }}
              transition={{
                x: {
                  repeat: Infinity,
                  repeatType: "loop",
                  duration: 30,
                  ease: "linear",
                },
              }}
            >
              {[...Array(2)].map((_, setIndex) => (
                <div key={setIndex} className="flex items-center gap-12 flex-shrink-0">
                  {[
                    { name: "Highlands Coffee", color: "from-red-600 to-orange-500" },
                    { name: "The Coffee House", color: "from-orange-600 to-yellow-500" },
                    { name: "Phúc Long", color: "from-green-600 to-emerald-500" },
                    { name: "KILO Fashion", color: "from-pink-600 to-rose-500" },
                    { name: "Coolmate", color: "from-blue-600 to-cyan-500" },
                    { name: "Routine", color: "from-purple-600 to-indigo-500" },
                    { name: "Canifa", color: "from-teal-600 to-green-500" },
                  ].map((company, i) => (
                    <div 
                      key={i} 
                      className={`px-8 py-4 bg-gradient-to-r ${company.color} rounded-xl opacity-20 hover:opacity-40 transition-opacity duration-300 flex-shrink-0`}
                    >
                      <span className="text-white font-bold text-lg whitespace-nowrap">
                        {company.name}
                      </span>
                    </div>
                  ))}
                </div>
              ))}
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}
