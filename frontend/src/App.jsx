import { useState, useEffect } from 'react'
import axios from 'axios'
import PlayerSelector from './components/PlayerSelector'
import GameSelector from './components/GameSelector'
import ModelComparison from './components/ModelComparison'
import './App.css'

const API_BASE_URL = 'http://localhost:8000/api'

function App() {
  const [players, setPlayers] = useState([])
  const [selectedPlayer, setSelectedPlayer] = useState('')
  const [gameDates, setGameDates] = useState([])
  const [selectedDate, setSelectedDate] = useState('')
  const [predictions, setPredictions] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

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

  // Fetch predictions when game date is selected
  const handleDateSelect = async (date) => {
    setSelectedDate(date)
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

  return (
    <div className="app">
      <header className="app-header">
        <h1>Aaronson Oracle Baseball</h1>
        <p>Predicting baseball pitches using pattern matching algorithms</p>
      </header>

      <main className="app-main">
        <div className="controls">
          <PlayerSelector
            players={players}
            selectedPlayer={selectedPlayer}
            onSelect={handlePlayerSelect}
            disabled={loading}
          />

          {gameDates.length > 0 && (
            <GameSelector
              dates={gameDates}
              selectedDate={selectedDate}
              onSelect={handleDateSelect}
              disabled={loading}
            />
          )}
        </div>

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

        {predictions && !loading && (
          <ModelComparison predictions={predictions} />
        )}
      </main>
    </div>
  )
}

export default App
