import axios from "axios";

// FastAPI DocAI backend runs on port 8000 with `/api` prefix
const BASE_URL = "http://localhost:8000/api";

export const processFile = async (file, action) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("action", action);

  const response = await axios.post(`${BASE_URL}/process/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data;
};

export const translateFile = async (file, targetLanguage) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("target_language", targetLanguage);

  const response = await axios.post(`${BASE_URL}/translate/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return response.data;
};
