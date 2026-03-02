import { useNavigate } from "react-router-dom";
import ThemeInput from "./ThemeInput";
import LoadingStatus from "./LoadingStatus";
import useStoryJob from "../hooks/useStoryJob";

function StoryGenerator() {
  const navigate = useNavigate();
  const { theme, status, error, generateStory } = useStoryJob(navigate);

  return (
    <div className="story-generator">

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {status === "idle" && (
        <ThemeInput onSubmit={generateStory} />
      )}

      {(status === "loading" || status === "processing") && (
        <LoadingStatus theme={theme} />
      )}

    </div>
  );
}

export default StoryGenerator;