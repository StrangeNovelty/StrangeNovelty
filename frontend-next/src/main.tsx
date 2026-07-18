import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";
import "./chat.css";
import "./character.css";
import "./world.css";
import "./workshop.css";
import "./modules.css";

const root = document.getElementById("story-engine-next-root");
if (!root) throw new Error("Story Engine root is unavailable.");
createRoot(root).render(
  <React.StrictMode>
    <BrowserRouter basename="/story-engine-next">
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
