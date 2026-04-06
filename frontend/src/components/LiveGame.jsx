import { useState, useEffect, useCallback, useRef } from 'react'
import PropTypes from 'prop-types'
import axios from 'axios'
import ModelComparison from './ModelComparison'

const API_BASE_URL = import.meta.env.MODE === 'production'
  ? '/api'
  : 'http://localhost:8000/api'

const POLL_INTERVAL = 30000 // 30 seconds

function LiveGame({ gamePk, pitcher, theme }) {
  const [predictions, setPredictions] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const intervalRef = useRef(null)

  const fetchLiveData = useCallback(async () => {
    try {
      const params = pitcher ? `?pitcher=${encodeURIComponent(pitcher)}` : ''
      const response = await axios.get(`${API_BASE_URL}/live/game/${gamePk}${params}`)
      setPredictions(response.data)
      setLastUpdated(new Date())
      setError(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch live game data')
    } finally {
      setLoading(false)
    }
  }, [gamePk, pitcher])

  // Initial fetch + polling
  useEffect(() => {
    setLoading(true)
    fetchLiveData()

    intervalRef.current = setInterval(fetchLiveData, POLL_INTERVAL)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchLiveData])

  if (loading && !predictions) {
    return <div className="loading">Loading live game data...</div>
  }

  if (error && !predictions) {
    return <div className="error-message">{error}</div>
  }

  return (
    <div className="live-game">
      <div className="live-indicator">
        <span className="live-dot" />
        <span className="live-text">LIVE</span>
        {lastUpdated && (
          <span className="last-updated">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        )}
        <button className="refresh-button" onClick={fetchLiveData}>
          Refresh
        </button>
      </div>

      {predictions && (
        <ModelComparison predictions={predictions} theme={theme} />
      )}
    </div>
  )
}

LiveGame.propTypes = {
  gamePk: PropTypes.number.isRequired,
  pitcher: PropTypes.string,
  theme: PropTypes.string,
}

export default LiveGame
