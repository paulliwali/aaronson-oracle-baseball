import PropTypes from 'prop-types'

const PITCH_BUTTONS = [
  { type: 'fast', label: 'Fastball', color: '#FF5252', key: 'F' },
  { type: 'breaking', label: 'Breaking', color: '#2196F3', key: 'B' },
  { type: 'off-speed', label: 'Off-Speed', color: '#4CAF50', key: 'O' },
]

function PitchGuessPanel({ onGuess, disabled, bestModelName, scores }) {
  return (
    <div className="guess-panel">
      {/* Scoreboard */}
      {scores && (
        <div className="scoreboard">
          <div className="score-item user-score">
            <div className="score-label">You</div>
            <div className="score-value">
              {scores.user.correct}/{scores.user.total}
              {scores.user.total > 0 && (
                <span className="score-pct">
                  {' '}({((scores.user.correct / scores.user.total) * 100).toFixed(0)}%)
                </span>
              )}
            </div>
          </div>
          <div className="score-vs">vs</div>
          <div className="score-item model-score">
            <div className="score-label">{scores.bestModel.name}</div>
            <div className="score-value">
              {scores.bestModel.correct}/{scores.bestModel.total}
              {scores.bestModel.total > 0 && (
                <span className="score-pct">
                  {' '}({((scores.bestModel.correct / scores.bestModel.total) * 100).toFixed(0)}%)
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Guess buttons */}
      <div className="guess-buttons">
        {PITCH_BUTTONS.map(({ type, label, color, key }) => (
          <button
            key={type}
            className="guess-button"
            style={{ '--btn-color': color, opacity: disabled ? 0.5 : 1 }}
            onClick={() => onGuess(type)}
            disabled={disabled}
          >
            <kbd className="key-hint">{key}</kbd> {label}
          </button>
        ))}
      </div>
    </div>
  )
}

PitchGuessPanel.propTypes = {
  onGuess: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
  bestModelName: PropTypes.string,
  scores: PropTypes.shape({
    user: PropTypes.shape({ correct: PropTypes.number, total: PropTypes.number }).isRequired,
    bestModel: PropTypes.shape({ name: PropTypes.string, correct: PropTypes.number, total: PropTypes.number }).isRequired,
  }),
}

export default PitchGuessPanel
