import PropTypes from 'prop-types'

function PlayerSelector({ players, selectedPlayer, onSelect, disabled }) {
  return (
    <div className="selector">
      <label htmlFor="player-select">Select Pitcher:</label>
      <select
        id="player-select"
        value={selectedPlayer}
        onChange={(e) => onSelect(e.target.value)}
        disabled={disabled}
      >
        <option value="">-- Choose a pitcher --</option>
        {players.map((player) => (
          <option key={player} value={player}>
            {player}
          </option>
        ))}
      </select>
    </div>
  )
}

PlayerSelector.propTypes = {
  players: PropTypes.arrayOf(PropTypes.string).isRequired,
  selectedPlayer: PropTypes.string.isRequired,
  onSelect: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}

export default PlayerSelector
