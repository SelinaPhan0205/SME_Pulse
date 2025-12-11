/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  // Thêm các env variables khác ở đây nếu cần
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
