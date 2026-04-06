import { useState, useEffect } from 'react'
import axios from 'axios'
import PlayerSelector from './components/PlayerSelector'
import GameSelector from './components/GameSelector'
import ModelComparison from './components/ModelComparison'
import PlaybackGame from './components/PlaybackGame'
import LiveGameSelector from './components/LiveGameSelector'
import LiveGame from './components/LiveGame'
import './App.css'

// Use relative URL in production, localhost in development
const API_BASE_URL = import.meta.env.MODE === 'production'
  ? '/api'
  : 'http://localhost:8000/api'

function App() {
  const [players, setPlayers] = useState([])
  const [selectedPlayer, setSelectedPlayer] = useState('')
  const [gameDates, setGameDates] = useState([])
  const [selectedDate, setSelectedDate] = useState('')
  const [predictions, setPredictions] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'backyard')
  const [mode, setMode] = useState('analyze') // 'analyze', 'play', or 'live'

  // Live mode state
  const [liveGames, setLiveGames] = useState([])
  const [selectedLiveGame, setSelectedLiveGame] = useState(null)
  const [selectedLivePitcher, setSelectedLivePitcher] = useState(null)

  useEffect(() => {
    localStorage.setItem('theme', theme)
  }, [theme])

  // Fetch available players on mount
  useEffect(() => {
    const fetchPlayers = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/players/list`)
        setPlayers(response.data.players)
      } catch (err) {
        setError('Failed to fetch players list')
      }
    }
    fetchPlayers()
  }, [])

  // Fetch live games when entering live mode
  useEffect(() => {
    if (mode !== 'live') return

    const fetchLiveGames = async () => {
      setLoading(true)
      setError(null)
      try {
        const response = await axios.get(`${API_BASE_URL}/live/games`)
        setLiveGames(response.data.games)
      } catch (err) {
        setError('Failed to fetch live games')
      } finally {
        setLoading(false)
      }
    }
    fetchLiveGames()
  }, [mode])

  // Fetch game dates when player is selected
  const handlePlayerSelect = async (playerName) => {
    setSelectedPlayer(playerName)
    setSelectedDate('')
    setPredictions(null)
    setLoading(true)
    setError(null)

    try {
      const response = await axios.post(`${API_BASE_URL}/players/stats`, {
        player_name: playerName
      })
      setGameDates(response.data.game_dates)
    } catch (err) {
      setError('Failed to fetch game dates')
    } finally {
      setLoading(false)
    }
  }

  // Fetch predictions when game date is selected (analyze mode only)
  const handleDateSelect = async (date) => {
    setSelectedDate(date)

    if (mode === 'play') {
      setPredictions(null)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await axios.post(`${API_BASE_URL}/predictions/game`, {
        player_name: selectedPlayer,
        game_date: date
      })
      setPredictions(response.data)
    } catch (err) {
      setError('Failed to fetch predictions')
    } finally {
      setLoading(false)
    }
  }

  const handleLiveGameSelect = (game) => {
    setSelectedLiveGame(game)
    // Default to home pitcher
    setSelectedLivePitcher(game.home_pitcher || null)
  }

  // When switching modes, clear state
  const handleModeSwitch = (newMode) => {
    setMode(newMode)
    setPredictions(null)
    setError(null)
    if (newMode !== 'live') {
      setSelectedLiveGame(null)
      setSelectedLivePitcher(null)
    }
  }

  return (
    <div className="app" data-theme={theme}>
      <header className="app-header">
        <div className="header-content">
          <h1>Aaronson Oracle Baseball</h1>
          <p>Finding a better trash can algorithm</p>
        </div>
        <button
          className="theme-toggle"
          onClick={() => setTheme(t => t === 'backyard' ? 'modern' : 'backyard')}
          title={`Switch to ${theme === 'backyard' ? 'modern' : 'backyard'} theme`}
        >
          {theme === 'backyard' ? 'Clean Mode' : 'Fun Mode'}
        </button>
      </header>

      <main className="app-main">
        <div className="mode-toggle">
          <button
            className={`mode-button ${mode === 'analyze' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('analyze')}
          >
            Analyze
          </button>
          <button
            className={`mode-button ${mode === 'play' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('play')}
          >
            Play
          </button>
          <button
            className={`mode-button ${mode === 'live' ? 'active' : ''}`}
            onClick={() => handleModeSwitch('live')}
          >
            Live
          </button>
        </div>

        {/* Analyze / Play mode: pitcher + game selectors */}
        {mode !== 'live' && (
          <div className="controls">
            <PlayerSelector
              players={players}
              selectedPlayer={selectedPlayer}
              onSelect={handlePlayerSelect}
              disabled={loading}
            />

            <GameSelector
              dates={gameDates}
              selectedDate={selectedDate}
              onSelect={handleDateSelect}
              disabled={loading || !selectedPlayer}
            />
          </div>
        )}

        {/* Live mode: game selector */}
        {mode === 'live' && !selectedLiveGame && (
          <LiveGameSelector
            games={liveGames}
            selectedGamePk={null}
            onSelect={handleLiveGameSelect}
            loading={loading}
          />
        )}

        {/* Live mode: pitcher selector for selected game */}
        {mode === 'live' && selectedLiveGame && (
          <div className="live-controls">
            <button
              className="back-button"
              onClick={() => { setSelectedLiveGame(null); setSelectedLivePitcher(null) }}
            >
              &larr; Back to games
            </button>
            <div className="live-pitcher-select">
              <label>Pitcher:</label>
              <select
                value={selectedLivePitcher || ''}
                onChange={(e) => setSelectedLivePitcher(e.target.value || null)}
              >
                <option value="">All pitchers</option>
                {selectedLiveGame.home_pitcher && (
                  <option value={selectedLiveGame.home_pitcher}>
                    {selectedLiveGame.home_pitcher} ({selectedLiveGame.home_team})
                  </option>
                )}
                {selectedLiveGame.away_pitcher && (
                  <option value={selectedLiveGame.away_pitcher}>
                    {selectedLiveGame.away_pitcher} ({selectedLiveGame.away_team})
                  </option>
                )}
              </select>
            </div>
          </div>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {loading && (
          <div className="loading">
            Loading...
          </div>
        )}

        {/* Analyze mode */}
        {mode === 'analyze' && predictions && !loading && (
          <ModelComparison predictions={predictions} theme={theme} />
        )}

        {/* Play mode */}
        {mode === 'play' && selectedPlayer && selectedDate && !loading && (
          <PlaybackGame playerName={selectedPlayer} gameDate={selectedDate} />
        )}

        {/* Live mode */}
        {mode === 'live' && selectedLiveGame && (
          <LiveGame
            gamePk={selectedLiveGame.game_pk}
            pitcher={selectedLivePitcher}
            theme={theme}
          />
        )}
      </main>
    </div>
  )
}

export default App
