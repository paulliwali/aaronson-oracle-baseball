import PropTypes from 'prop-types'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, Cell, ReferenceLine, Label } from 'recharts'

// Backyard Baseball vibrant palette
const MODEL_COLORS = ['#D32F2F', '#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#C2185B']
const PITCH_TYPE_COLORS = {
  'fast': '#FF5252',      // bright red
  'breaking': '#2196F3',  // bright blue
  'off-speed': '#4CAF50'  // bright green
}

function ModelComparison({ predictions }) {
  const { player_name, game_date, home_team, away_team, pitcher_team, total_pitches, pitch_types_distribution, actual_pitches, models } = predictions

  // Transform data for the rolling accuracy chart
  const chartData = Array.from({ length: total_pitches }, (_, i) => {
    const dataPoint = { pitch: i + 1 }
    models.forEach((model) => {
      dataPoint[model.model_name] = model.rolling_accuracy[i]
    })
    return dataPoint
  })

  // Transform data for pitch predictions scatter plot
  const pitchPredictionData = Array.from({ length: total_pitches }, (_, i) => {
    const dataPoint = { pitch: i + 1, actual: actual_pitches[i] }
    models.forEach((model) => {
      dataPoint[`${model.model_name}_pred`] = model.predictions[i]
    })
    return dataPoint
  })

  // Create rows for the pitch prediction visualization
  const getPitchTypeValue = (pitchType) => {
    const mapping = { 'fast': 0, 'breaking': 1, 'off-speed': 2 }
    return mapping[pitchType] ?? 0
  }

  const pitchScatterData = []

  // Add actual pitches at the top (highest y value)
  actual_pitches.forEach((pitch, i) => {
    pitchScatterData.push({
      pitch: i + 1,
      y: models.length + 0.5,
      pitchType: pitch,
      label: 'Actual'
    })
  })

  // Add predictions for each model (reversed order so first model is closer to actual)
  models.forEach((model, modelIndex) => {
    model.predictions.forEach((prediction, i) => {
      pitchScatterData.push({
        pitch: i + 1,
        y: models.length - modelIndex - 0.5,
        pitchType: prediction,
        label: model.model_name
      })
    })
  })

  return (
    <div className="model-comparison">
      <h2>Game Analysis</h2>
      <div className="game-info">
        <p><strong>Pitcher:</strong> {player_name} ({pitcher_team})</p>
        <p><strong>Date:</strong> {new Date(game_date).toLocaleDateString()}</p>
        <p><strong>Matchup:</strong> {away_team} @ {home_team}</p>
        <p><strong>Total Pitches:</strong> {total_pitches}</p>
      </div>

      <div className="pitch-distribution">
        <h3>Pitch Type Distribution</h3>
        <div className="distribution-grid">
          {Object.entries(pitch_types_distribution).map(([type, count]) => (
            <div key={type} className="distribution-item">
              <span className="pitch-type">{type}</span>
              <span className="pitch-count">{count} ({Math.round(count / total_pitches * 100)}%)</span>
            </div>
          ))}
        </div>
      </div>

      <div className="pitch-predictions-chart">
        <h3>Pitch Predictions vs Actual</h3>
        <ResponsiveContainer width="100%" height={200 + models.length * 40}>
          <ScatterChart margin={{ top: 20, right: 100, bottom: 50, left: 150 }}>
            <CartesianGrid strokeDasharray="5 5" stroke="#1976D2" strokeWidth={2} horizontal={false} />
            <XAxis
              type="number"
              dataKey="pitch"
              name="Pitch Number"
              domain={[1, total_pitches]}
              tick={{ fontSize: 14, fontWeight: 700, fill: '#1976D2' }}
              tickCount={10}
              stroke="#1976D2"
              strokeWidth={3}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Model"
              domain={[0, models.length + 1]}
              ticks={[models.length + 0.5, ...models.map((_, i) => models.length - i - 0.5)]}
              tick={{ fontSize: 14, fontWeight: 700, fill: '#1976D2' }}
              tickFormatter={(value) => {
                if (value === models.length + 0.5) return 'Actual'
                const modelIndex = models.length - Math.ceil(value)
                return models[modelIndex]?.model_name || ''
              }}
              stroke="#1976D2"
              strokeWidth={3}
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3', stroke: '#FF6B35', strokeWidth: 3 }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div style={{
                      backgroundColor: '#FFEB3B',
                      padding: '12px 16px',
                      border: '4px solid #FF6B35',
                      borderRadius: '12px',
                      boxShadow: '0 4px 0 #FFA500'
                    }}>
                      <p style={{ margin: 0, fontWeight: 900, marginBottom: '6px', color: '#D32F2F', fontSize: '1.1rem' }}>Pitch #{data.pitch}</p>
                      <p style={{ margin: 0, fontWeight: 700, color: '#1976D2' }}>{data.label}: <span style={{ color: PITCH_TYPE_COLORS[data.pitchType], fontWeight: 900 }}>{data.pitchType}</span></p>
                    </div>
                  )
                }
                return null
              }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              content={() => (
                <div className="pitch-legend">
                  <div className="legend-item">
                    <span className="legend-dot" style={{ backgroundColor: PITCH_TYPE_COLORS.fast }}></span>
                    <span>Fast</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot" style={{ backgroundColor: PITCH_TYPE_COLORS.breaking }}></span>
                    <span>Breaking</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot" style={{ backgroundColor: PITCH_TYPE_COLORS['off-speed'] }}></span>
                    <span>Off-Speed</span>
                  </div>
                </div>
              )}
            />
            <Scatter data={pitchScatterData} shape="circle">
              {pitchScatterData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={PITCH_TYPE_COLORS[entry.pitchType]}
                  stroke="#333"
                  strokeWidth={2}
                />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="rolling-accuracy-chart">
        <h3>Rolling Accuracy Over Game</h3>
        <ResponsiveContainer width="100%" height={450}>
          <LineChart data={chartData} margin={{ top: 20, right: 100, bottom: 50, left: 150 }}>
            <CartesianGrid strokeDasharray="5 5" stroke="#9C27B0" strokeWidth={2} horizontal={false} />
            <XAxis
              type="number"
              dataKey="pitch"
              domain={[1, total_pitches]}
              tick={{ fontSize: 14, fontWeight: 700, fill: '#1976D2' }}
              tickCount={10}
              stroke="#9C27B0"
              strokeWidth={3}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fontSize: 14, fontWeight: 700, fill: '#1976D2' }}
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              stroke="#9C27B0"
              strokeWidth={3}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div style={{
                      backgroundColor: '#FFEB3B',
                      padding: '12px 16px',
                      border: '4px solid #FF6B35',
                      borderRadius: '12px',
                      boxShadow: '0 4px 0 #FFA500'
                    }}>
                      <p style={{ margin: 0, fontWeight: 900, marginBottom: '8px', color: '#D32F2F', fontSize: '1.1rem' }}>Pitch #{label}</p>
                      {payload.map((entry, index) => {
                        const modelData = models.find(m => m.model_name === entry.dataKey)
                        const finalAccuracy = modelData ? (modelData.accuracy * 100).toFixed(1) : '0.0'
                        return (
                          <p key={index} style={{ margin: 0, color: entry.color, marginBottom: '2px', fontWeight: 700 }}>
                            <strong>{entry.dataKey}:</strong> {(entry.value * 100).toFixed(2)}% (Final: {finalAccuracy}%)
                          </p>
                        )
                      })}
                    </div>
                  )
                }
                return null
              }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              wrapperStyle={{ paddingTop: '20px', fontWeight: 700, fontSize: '14px' }}
            />
            {models.map((model, index) => (
              <Line
                key={model.model_name}
                type="monotone"
                dataKey={model.model_name}
                stroke={MODEL_COLORS[index % MODEL_COLORS.length]}
                dot={false}
                strokeWidth={4}
                name={model.model_name}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

ModelComparison.propTypes = {
  predictions: PropTypes.shape({
    player_name: PropTypes.string.isRequired,
    game_date: PropTypes.string.isRequired,
    home_team: PropTypes.string.isRequired,
    away_team: PropTypes.string.isRequired,
    pitcher_team: PropTypes.string.isRequired,
    total_pitches: PropTypes.number.isRequired,
    pitch_types_distribution: PropTypes.object.isRequired,
    actual_pitches: PropTypes.arrayOf(PropTypes.string).isRequired,
    models: PropTypes.arrayOf(
      PropTypes.shape({
        model_name: PropTypes.string.isRequired,
        accuracy: PropTypes.number.isRequired,
        rolling_accuracy: PropTypes.arrayOf(PropTypes.number).isRequired,
        predictions: PropTypes.arrayOf(PropTypes.string).isRequired,
      })
    ).isRequired,
  }).isRequired,
}

export default ModelComparison
