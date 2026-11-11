import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter";
// opsz.css includes the optical-size axis used by font-variation-settings.
import "@fontsource-variable/fraunces/opsz.css";
import "./styles/tokens.css";
import "./styles/global.css";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
