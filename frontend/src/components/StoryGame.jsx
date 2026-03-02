import { useState, useEffect, useMemo, useCallback } from "react";

function StoryGame({ story, onNewStory }) {
  const [currentNodeId, setCurrentNodeId] = useState(null);

  // Initialize root node when story changes
  useEffect(() => {
    if (story?.root_node?.id) {
      setCurrentNodeId(story.root_node.id);
    }
  }, [story]);

  // ✅ Derived node (no extra state)
  const currentNode = useMemo(() => {
    if (!story?.all_nodes || !currentNodeId) return null;
    return story.all_nodes[currentNodeId] || null;
  }, [story, currentNodeId]);

  const isEnding = currentNode?.is_ending ?? false;
  const isWinningEnding = currentNode?.is_winning_ending ?? false;

  const options = useMemo(() => {
    if (!currentNode || currentNode.is_ending) return [];
    return currentNode.options ?? [];
  }, [currentNode]);

  // ✅ Stable function references
  const chooseOption = useCallback((nodeId) => {
    setCurrentNodeId(nodeId);
  }, []);

  const restartStory = useCallback(() => {
    if (story?.root_node?.id) {
      setCurrentNodeId(story.root_node.id);
    }
  }, [story]);

  if (!story) return null;

  return (
    <div className="story-game">
      <header className="story-header">
        <h2>{story.title}</h2>
      </header>

      <div className="story-content">
        {currentNode && (
          <div className="story-node">
            <p>{currentNode.content}</p>

            {isEnding ? (
              <div className="story-ending">
                <h3>
                  {isWinningEnding ? "Congratulations 🎉" : "The End"}
                </h3>
                <p>
                  {isWinningEnding
                    ? "You reached a winning ending!"
                    : "Your adventure has ended."}
                </p>
              </div>
            ) : (
              <div className="story-options">
                <h3>What will you do?</h3>
                <div className="options-list">
                  {options.map((option) => (
                    <button
                      key={option.node_id}  
                      onClick={() => chooseOption(option.node_id)}
                      className="option-btn"
                    >
                      {option.text}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        <div className="story-controls">
          <button onClick={restartStory} className="reset-btn">
            Restart Story
          </button>
        </div>

        {onNewStory && (
          <button onClick={onNewStory} className="new-story-btn">
            New Story
          </button>
        )}
      </div>
    </div>
  );
}

export default StoryGame;