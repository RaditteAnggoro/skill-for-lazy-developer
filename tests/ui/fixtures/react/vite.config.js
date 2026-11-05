import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

const reactDir = fileURLToPath(new URL("./node_modules/react", import.meta.url));
const reactDomDir = fileURLToPath(new URL("./node_modules/react-dom", import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: /^react\/jsx-runtime$/, replacement: reactDir + "/jsx-runtime.js" },
      { find: /^react$/, replacement: reactDir },
      { find: /^react-dom\/client$/, replacement: reactDomDir + "/client.js" },
      { find: /^react-dom$/, replacement: reactDomDir },
    ],
  },
});
