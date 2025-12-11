import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// ⚠️ MSW DISABLED - Using Real Backend APIs
// Uncomment below to re-enable mock service worker for development

// async function enableMocking() {
//   if (import.meta.env.MODE !== 'development') {
//     return;
//   }
//   const { worker } = await import('./mocks/browser');
//   return worker.start({
//     onUnhandledRequest: 'bypass',
//   });
// }

// enableMocking().then(() => {
//   createRoot(document.getElementById("root")!).render(<App />);
// });

// ✅ Direct rendering - Real API integration
createRoot(document.getElementById("root")!).render(<App />);
  