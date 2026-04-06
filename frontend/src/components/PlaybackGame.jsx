import { useState, useCallback, useRef, useEffect } from 'react'
import PropTypes from 'prop-types'
import axios from 'axios'
import PitchGuessPanel from './PitchGuessPanel'

const API_BASE_URL = import.meta.env.MODE === 'production'
  ? '/api'
  : 'http://localhost:8000/api'

const PITCH_COLORS = { fast: '#FF5252', breaking: '#2196F3', 'off-speed': '#4CAF50' }

const MODEL_PRIORITY = ['Transformer', 'Random Forest', 'Markov Context', 'N-Gram (n=4)']

function pickBestModel(modelPredictions) {
  if (!modelPredictions) return { name: 'Model', pred: 'fast' }
  const names = Object.keys(modelPredictions)
  for (const prio of MODEL_PRIORITY) {
    const match = names.find(n => n.includes(prio) || n === prio)
    if (match) return { name: match, pred: modelPredictions[match] }
  }
  const name = names[0] || 'Model'
  return { name, pred: modelPredictions[name] || 'fast' }
}

// Group pitch history entries by at-bat
function groupByAtBat(entries) {
  const groups = []
  let current = null
  for (const entry of entries) {
    if (!current || current.ab !== entry.ab) {
      current = { ab: entry.ab, pitches: [] }
      groups.push(current)
    }
    current.pitches.push(entry)
  }
  return groups
}

function PlaybackGame({ playerName, gameDate }) {
  const [pitchIndex, setPitchIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [bestModelPred, setBestModelPred] = useState(null)
  const [bestModelName, setBestModelName] = useState('Model')
  const [gameContext, setGameContext] = useState(null)
  const [totalPitches, setTotalPitches] = useState(null)
  const [isLastPitch, setIsLastPitch] = useState(false)
  const [gameOver, setGameOver] = useState(false)
  const [started, setStarted] = useState(false)

  // Full pitch history with guess results
  // Each entry: { pitch, ab, userGuess?, modelGuess?, userCorrect?, modelCorrect? }
  const [pitchHistory, setPitchHistory] = useState([])
  const [hasGuessedCurrent, setHasGuessedCurrent] = useState(false)

  const [userScore, setUserScore] = useState({ correct: 0, total: 0 })
  const [modelScore, setModelScore] = useState({ correct: 0, total: 0 })

  const chosenModel = useRef(null)
  const pendingGuess = useRef(false)
  const gameDataCache = useRef(null)

  const fetchPitchContext = useCallback(async (idx) => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.post(`${API_BASE_URL}/predictions/pitch`, {
        player_name: playerName,
        game_date: gameDate,
        pitch_index: idx,
      })
      const data = response.data
      gameDataCache.current = data
      setGameContext(data.game_context)
      setTotalPitches(data.total_pitches)
      setIsLastPitch(data.is_last_pitch)

      if (!chosenModel.current) {
        const best = pickBestModel(data.model_predictions)
        chosenModel.current = best.name
        setBestModelName(best.name)
      }

      setBestModelPred(data.model_predictions[chosenModel.current] || 'fast')
      setHasGuessedCurrent(false)
      pendingGuess.current = false

      // Build history from revealed pitches (pre-game pitches without guess data)
      if (idx === 0) {
        setPitchHistory([])
      }

      return data
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch pitch data')
      return null
    } finally {
      setLoading(false)
    }
  }, [playerName, gameDate])

  const startGame = useCallback(async () => {
    setStarted(true)
    setPitchIndex(0)
    setUserScore({ correct: 0, total: 0 })
    setModelScore({ correct: 0, total: 0 })
    setPitchHistory([])
    chosenModel.current = null
    gameDataCache.current = null
    setGameOver(false)
    setHasGuessedCurrent(false)
    pendingGuess.current = false
    await fetchPitchContext(0)
  }, [fetchPitchContext])

  // Auto-restart when gameDate changes
  useEffect(() => {
    if (playerName && gameDate) {
      startGame()
    }
  }, [playerName, gameDate, startGame])

  const processGuess = useCallback((guess, data) => {
    const actual = data.actual_pitch
    const modelPred = data.model_predictions[chosenModel.current] || 'fast'
    setBestModelPred(modelPred)

    const userCorrect = guess === actual
    const modelCorrect = modelPred === actual

    // Add to history
    setPitchHistory(prev => [...prev, {
      pitch: actual,
      ab: data.game_context.at_bat_number,
      userGuess: guess,
      modelGuess: modelPred,
      userCorrect,
      modelCorrect,
    }])

    setHasGuessedCurrent(true)
    setUserScore(prev => ({ correct: prev.correct + (userCorrect ? 1 : 0), total: prev.total + 1 }))
    setModelScore(prev => ({ correct: prev.correct + (modelCorrect ? 1 : 0), total: prev.total + 1 }))

    if (data.is_last_pitch) setGameOver(true)
  }, [])

  const handleGuess = useCallback(async (guess) => {
    if (pendingGuess.current || loading) return
    pendingGuess.current = true

    // Already guessed current pitch — advance to next and guess
    if (hasGuessedCurrent && !isLastPitch) {
      const nextIdx = pitchIndex + 1
      setPitchIndex(nextIdx)
      setHasGuessedCurrent(false)

      setLoading(true)
      try {
        const response = await axios.post(`${API_BASE_URL}/predictions/pitch`, {
          player_name: playerName,
          game_date: gameDate,
          pitch_index: nextIdx,
        })
        const data = response.data
        gameDataCache.current = data
        setGameContext(data.game_context)
        setTotalPitches(data.total_pitches)
        setIsLastPitch(data.is_last_pitch)
        setBestModelPred(data.model_predictions[chosenModel.current] || 'fast')

        processGuess(guess, data)
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to fetch pitch data')
      } finally {
        setLoading(false)
        pendingGuess.current = false
      }
      return
    }

    // First guess on this pitch
    const data = gameDataCache.current
    if (!data) { pendingGuess.current = false; return }

    processGuess(guess, data)
    pendingGuess.current = false
  }, [hasGuessedCurrent, isLastPitch, pitchIndex, playerName, gameDate, loading, processGuess])

  // Skip to next at-bat
  const skipToNextAB = useCallback(async () => {
    if (!gameDataCache.current || isLastPitch || gameOver) return

    const currentBatter = gameDataCache.current.game_context.batter_name
    let idx = pitchIndex

    // If we haven't guessed current pitch, skip it too
    if (!hasGuessedCurrent) {
      const data = gameDataCache.current
      // Auto-guess as "fast" for skipped pitch
      processGuess('fast', data)
    }

    while (idx < gameDataCache.current.total_pitches - 1) {
      idx++
      const response = await axios.post(`${API_BASE_URL}/predictions/pitch`, {
        player_name: playerName,
        game_date: gameDate,
        pitch_index: idx,
      })
      const data = response.data

      if (data.game_context.batter_name !== currentBatter) {
        gameDataCache.current = data
        setPitchIndex(idx)
        setGameContext(data.game_context)
        setTotalPitches(data.total_pitches)
        setIsLastPitch(data.is_last_pitch)
        setBestModelPred(data.model_predictions[chosenModel.current] || 'fast')
        setHasGuessedCurrent(false)
        pendingGuess.current = false
        return
      }

      // Auto-guess skipped pitches
      processGuess('fast', data)
    }

    setGameOver(true)
  }, [pitchIndex, playerName, gameDate, isLastPitch, gameOver, hasGuessedCurrent, processGuess])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (gameOver || loading || !started) return
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return

      switch (e.key) {
        case '1': case 'f': case 'F':
          e.preventDefault(); handleGuess('fast'); break
        case '2': case 'b': case 'B':
          e.preventDefault(); handleGuess('breaking'); break
        case '3': case 'o': case 'O':
          e.preventDefault(); handleGuess('off-speed'); break
        case 'Tab':
          e.preventDefault(); skipToNextAB(); break
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleGuess, skipToNextAB, gameOver, loading, started])

  if (!started) {
    return (
      <div className="playback-game">
        <div className="playback-start">
          <h2>Pitch Prediction Challenge</h2>
          <p>
            Step through <strong>{playerName}</strong>'s game on <strong>{gameDate}</strong> pitch by pitch.
            Guess each pitch and compete against our best prediction model!
          </p>
          <button className="start-button" onClick={startGame}>Start Game</button>
        </div>
      </div>
    )
  }

  if (gameOver) {
    const userPct = userScore.total > 0 ? ((userScore.correct / userScore.total) * 100).toFixed(1) : '0'
    const modelPct = modelScore.total > 0 ? ((modelScore.correct / modelScore.total) * 100).toFixed(1) : '0'
    const userWins = parseFloat(userPct) > parseFloat(modelPct)

    return (
      <div className="playback-game">
        <div className="game-over-panel">
          <h2>Game Over!</h2>
          <div className="final-scores">
            <div className={`final-score-card ${userWins ? 'winner' : ''}`}>
              <div className="final-score-label">You</div>
              <div className="final-score-value">{userScore.correct}/{userScore.total}</div>
              <div className="final-score-pct">{userPct}%</div>
            </div>
            <div className="final-vs">vs</div>
            <div className={`final-score-card ${!userWins ? 'winner' : ''}`}>
              <div className="final-score-label">{bestModelName}</div>
              <div className="final-score-value">{modelScore.correct}/{modelScore.total}</div>
              <div className="final-score-pct">{modelPct}%</div>
            </div>
          </div>
          <button className="start-button" onClick={startGame}>Play Again</button>
        </div>
      </div>
    )
  }

  const abGroups = groupByAtBat(pitchHistory)
  const recentGroups = abGroups.slice(-6)

  return (
    <div className="playback-game">
      {error && <div className="error-message">{error}</div>}

      {gameContext && (
        <div className="playback-context">
          <div className="context-header">
            <span className="pitch-counter">
              Pitch {pitchIndex + 1}{totalPitches ? ` / ${totalPitches}` : ''}
            </span>
            {gameContext.batter_name && (
              <span className="context-batter">
                AB: <strong>{gameContext.batter_name}</strong>
              </span>
            )}
          </div>

          <div className="context-grid">
            <div className="context-item">
              <span className="context-label">Count</span>
              <span className="context-value">{gameContext.balls}-{gameContext.strikes}</span>
            </div>
            <div className="context-item">
              <span className="context-label">Outs</span>
              <span className="context-value">{gameContext.outs}</span>
            </div>
            <div className="context-item">
              <span className="context-label">Inning</span>
              <span className="context-value">{gameContext.inning_half === 'Top' ? '▲' : '▼'} {gameContext.inning}</span>
            </div>
            <div className="context-item">
              <span className="context-label">Score</span>
              <span className="context-value">{gameContext.home_score}-{gameContext.away_score}</span>
            </div>
          </div>

          {/* Pitch history with guess results */}
          {recentGroups.length > 0 && (
            <div className="pitch-history">
              <div className="history-groups">
                {recentGroups.map((group, gi) => (
                  <div key={gi} className="history-ab-group">
                    {group.pitches.map((entry, pi) => (
                      <div key={pi} className="history-pitch-item">
                        <span
                          className="history-pitch"
                          style={{ backgroundColor: PITCH_COLORS[entry.pitch] || '#999' }}
                          title={entry.pitch}
                        >
                          {entry.pitch[0].toUpperCase()}
                        </span>
                        <div className="history-guesses">
                          <span
                            className={`guess-indicator ${entry.userCorrect ? 'correct' : 'wrong'}`}
                            title={`You: ${entry.userGuess}`}
                          >Y</span>
                          <span
                            className={`guess-indicator ${entry.modelCorrect ? 'correct' : 'wrong'}`}
                            title={`${bestModelName}: ${entry.modelGuess}`}
                          >M</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="loading">Loading...</div>
      ) : (
        <PitchGuessPanel
          onGuess={handleGuess}
          disabled={loading}
          bestModelName={bestModelName}
          scores={{
            user: userScore,
            bestModel: { name: bestModelName, ...modelScore },
          }}
        />
      )}

      {!gameOver && started && (
        <div className="keyboard-hint">
          <kbd>Tab</kbd> skip to next AB
        </div>
      )}
    </div>
  )
}

PlaybackGame.propTypes = {
  playerName: PropTypes.string.isRequired,
  gameDate: PropTypes.string.isRequired,
}

export default PlaybackGame
