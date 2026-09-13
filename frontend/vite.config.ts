import { defineConfig, type UserConfig } from "vite";
import react from "@vitejs/plugin-react";

const config: UserConfig = {
  plugins: [react()],
  server: {
    port: 5175,
    proxy: {
      "/api": "http://localhost:8011",
    },
  },
};

export default defineConfig(config);
