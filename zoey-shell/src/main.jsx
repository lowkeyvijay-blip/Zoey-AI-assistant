import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { ZoeyProvider } from "./store/ZoeyProvider.jsx";
import "./styles/theme.css";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ZoeyProvider>
      <App />
    </ZoeyProvider>
  </StrictMode>
);
