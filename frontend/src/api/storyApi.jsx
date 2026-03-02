import axios from "axios";
import { API_BASE_URL } from "../utils";

export const createStory = async (theme) => {
  const response = await axios.post(
    `${API_BASE_URL}/stories/create`,
    { theme }
  );
  return response.data;
};

export const getJobStatus = async (jobId) => {
  const response = await axios.get(
    `${API_BASE_URL}/jobs/${jobId}`
  );
  return response.data;
};