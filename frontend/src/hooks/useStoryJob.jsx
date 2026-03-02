import { useState, useEffect, useCallback } from "react";
import { createStory, getJobStatus } from "../api/storyApi";

export default function useStoryJob(navigate) {
  const [theme, setTheme] = useState("");
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState("idle"); 
  // idle | loading | processing | error
  const [error, setError] = useState(null);

  const generateStory = async (themeValue) => {
    try {
      setStatus("loading");
      setError(null);

      const { job_id, status } = await createStory(themeValue);

      setTheme(themeValue);
      setJobId(job_id);
      setStatus(status);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to generate story");
      setStatus("error");
    }
  };

  const pollJob = useCallback(async () => {
    if (!jobId) return;

    try {
      const data = await getJobStatus(jobId);

      setStatus(data.status);

      if (data.status === "completed" && data.story_id) {
        navigate(`/story/${data.story_id}`);
      }

      if (data.status === "failed") {
        setError(data.error || "Story generation failed");
        setStatus("error");
      }
    } catch {
      setError("Failed to check job status");
      setStatus("error");
    }
  }, [jobId, navigate]);

  useEffect(() => {
    if (status !== "processing") return;

    const interval = setInterval(pollJob, 5000);
    return () => clearInterval(interval);
  }, [status, pollJob]);

  return { theme, status, error, generateStory };
}