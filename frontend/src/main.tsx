import React from "react";
import ReactDOM from "react-dom/client";

import App from "@/App";
import { Toaster } from "@/components/ui/sonner";
import "@/index.css";

// Apply the persisted (or default dark) theme before first paint.
const storedTheme = window.localStorage.getItem("ai-swe-theme");
document.documentElement.classList.add(storedTheme === "light" ? "light" : "dark");

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
    <Toaster />
  </React.StrictMode>,
);
