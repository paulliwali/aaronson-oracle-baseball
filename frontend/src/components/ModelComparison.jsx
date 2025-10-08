import PropTypes from 'prop-types'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, Cell, ReferenceLine, Label } from 'recharts'

// Colorful muted palette
const MODEL_COLORS = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981']
const PITCH_TYPE_COLORS = {
  'fast': '#ef4444',      // bright red
  'breaking': '#3b82f6',  // bright blue
  'off-speed': '#22c55e'  // bright green
}

function ModelComparison({ predictions }) {
  const { player_name, game_date, total_pitches, pitch_types_distribution, actual_pitches, models } = predictions

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
        <p><strong>Pitcher:</strong> {player_name}</p>
        <p><strong>Date:</strong> {new Date(game_date).toLocaleDateString()}</p>
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
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              type="number"
              dataKey="pitch"
              name="Pitch Number"
              domain={[1, total_pitches]}
              tick={{ fontSize: 12 }}
              tickCount={10}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Model"
              domain={[0, models.length + 1]}
              ticks={[models.length + 0.5, ...models.map((_, i) => models.length - i - 0.5)]}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => {
                if (value === models.length + 0.5) return 'Actual'
                const modelIndex = models.length - Math.ceil(value)
                return models[modelIndex]?.model_name || ''
              }}
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div style={{
                      backgroundColor: 'white',
                      padding: '10px',
                      border: '1px solid #cbd5e1',
                      borderRadius: '6px',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                    }}>
                      <p style={{ margin: 0, fontWeight: 600, marginBottom: '4px' }}>Pitch #{data.pitch}</p>
                      <p style={{ margin: 0 }}>{data.label}: <span style={{ color: PITCH_TYPE_COLORS[data.pitchType], fontWeight: 600 }}>{data.pitchType}</span></p>
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
                <Cell key={`cell-${index}`} fill={PITCH_TYPE_COLORS[entry.pitchType]} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="rolling-accuracy-chart">
        <h3>Rolling Accuracy Over Game</h3>
        <ResponsiveContainer width="100%" height={450}>
          <LineChart data={chartData} margin={{ top: 20, right: 100, bottom: 50, left: 150 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="pitch"
              domain={[1, total_pitches]}
              tick={{ fontSize: 12 }}
              tickCount={10}
              label={{ value: 'Pitch Number', position: 'insideBottom', offset: -10, fontSize: 14 }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              label={{ value: 'Accuracy', angle: -90, position: 'insideLeft', fontSize: 14 }}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div style={{
                      backgroundColor: 'white',
                      padding: '10px',
                      border: '1px solid #cbd5e1',
                      borderRadius: '6px',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                    }}>
                      <p style={{ margin: 0, fontWeight: 600, marginBottom: '8px' }}>Pitch #{label}</p>
                      {payload.map((entry, index) => {
                        const modelData = models.find(m => m.model_name === entry.dataKey)
                        const finalAccuracy = modelData ? (modelData.accuracy * 100).toFixed(1) : '0.0'
                        return (
                          <p key={index} style={{ margin: 0, color: entry.color, marginBottom: '2px' }}>
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
              wrapperStyle={{ paddingTop: '20px' }}
            />
            {models.map((model, index) => (
              <Line
                key={model.model_name}
                type="monotone"
                dataKey={model.model_name}
                stroke={MODEL_COLORS[index % MODEL_COLORS.length]}
                dot={false}
                strokeWidth={2.5}
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
