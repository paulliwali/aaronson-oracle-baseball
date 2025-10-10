import PropTypes from 'prop-types'

function GameSelector({ dates, selectedDate, onSelect, disabled }) {
  return (
    <div className="selector">
      <label htmlFor="date-select">Select Game Date:</label>
      <select
        id="date-select"
        value={selectedDate}
        onChange={(e) => onSelect(e.target.value)}
        disabled={disabled}
      >
        <option value="">-- Choose a game date --</option>
        {dates.map((date) => (
          <option key={date} value={date}>
            {new Date(date).toLocaleDateString()}
          </option>
        ))}
      </select>
    </div>
  )
}

GameSelector.propTypes = {
  dates: PropTypes.arrayOf(PropTypes.string).isRequired,
  selectedDate: PropTypes.string.isRequired,
  onSelect: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
}

export default GameSelector
