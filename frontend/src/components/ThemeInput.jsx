import { useState, useRef } from "react"

function ThemeInput({ onSubmit }) {
    const [theme, setTheme] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    // Rate limiting state
    const submitCount = useRef(0);
    const lastResetTime = useRef(Date.now());
    const RATE_LIMIT = 5;        // max 5 requests
    const RATE_WINDOW = 60000;   // per 60 seconds

    const checkRateLimit = () => {
        const now = Date.now();

        // Window reset ho gayi? Counter reset karo
        if (now - lastResetTime.current > RATE_WINDOW) {
            submitCount.current = 0;
            lastResetTime.current = now;
        }

        if (submitCount.current >= RATE_LIMIT) {
            const waitSeconds = Math.ceil(
                (RATE_WINDOW - (now - lastResetTime.current)) / 1000
            );
            setError(`Too many requests. ${waitSeconds}s baad try karo.`);
            return false;
        }

        submitCount.current += 1;
        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!theme.trim()) {
            setError("Please enter a theme name");
            return;
        }

        // Rate limit check
        if (!checkRateLimit()) return;

        const sanitized = theme.trim().replace(/[<>]/g, "");

        setLoading(true);
        await onSubmit(sanitized);
        setLoading(false);
    };

    return (
        <div className="theme-input-container">
            <h2>Generate Your Adventure</h2>
            <p>Enter a theme for your interactive story</p>

            <div className="input-group">
                <input
                    type="text"
                    value={theme}
                    onChange={(e) => {
                        setTheme(e.target.value);
                        if (error) setError("");
                    }}
                    placeholder="Enter a theme (e.g. pirates, space, medieval...)"
                    className={error ? "error" : ""}
                    maxLength={100}
                    aria-describedby={error ? "theme-error" : undefined}
                    aria-invalid={!!error}
                />
                {error && (
                    <p id="theme-error" className="error-text">
                        {error}
                    </p>
                )}
            </div>

            <button
                onClick={handleSubmit}
                className="generate-btn"
                disabled={loading}
            >
                {loading ? "Generating..." : "Generate Story"}
            </button>
        </div>
    );
}

export default ThemeInput;
