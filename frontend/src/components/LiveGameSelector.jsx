import PropTypes from 'prop-types'

const STATUS_COLORS = {
  'In Progress': '#4CAF50',
  'Final': '#9E9E9E',
  'Pre-Game': '#FF9800',
  'Warmup': '#FF9800',
  'Scheduled': '#2196F3',
}

function LiveGameSelector({ games, selectedGamePk, onSelect, loading }) {
  if (!games || games.length === 0) {
    return (
      <div className="live-game-selector">
        <p className="no-games">No games scheduled for today.</p>
      </div>
    )
  }

  return (
    <div className="live-game-selector">
      <div className="live-games-grid">
        {games.map((game) => {
          const isSelected = game.game_pk === selectedGamePk
          const statusColor = STATUS_COLORS[game.status] || '#9E9E9E'

          return (
            <button
              key={game.game_pk}
              className={`live-game-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelect(game)}
              disabled={loading}
            >
              <div className="game-status" style={{ backgroundColor: statusColor }}>
                {game.status}
                {game.inning && ` - ${game.inning_half === 'Top' ? '▲' : game.inning_half === 'Bottom' ? '▼' : ''} ${game.inning}`}
              </div>
              <div className="game-matchup">
                <div className="team-row">
                  <span className="team-name">{game.away_team}</span>
                  <span className="team-score">{game.away_score}</span>
                </div>
                <div className="team-row">
                  <span className="team-name">{game.home_team}</span>
                  <span className="team-score">{game.home_score}</span>
                </div>
              </div>
              <div className="game-pitchers">
                {game.away_pitcher && (
                  <div className="pitcher-info">
                    <span className="pitcher-label">Away:</span> {game.away_pitcher}
                  </div>
                )}
                {game.home_pitcher && (
                  <div className="pitcher-info">
                    <span className="pitcher-label">Home:</span> {game.home_pitcher}
                  </div>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

LiveGameSelector.propTypes = {
  games: PropTypes.array,
  selectedGamePk: PropTypes.number,
  onSelect: PropTypes.func.isRequired,
  loading: PropTypes.bool,
}

export default LiveGameSelector
