import { useRef } from 'react'
import PropTypes from 'prop-types'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, Cell, ReferenceLine, Label } from 'recharts'

const THEME_PALETTES = {
  backyard: {
    models: ['#D32F2F', '#1976D2', '#388E3C', '#F57C00', '#7B1FA2', '#C2185B'],
    pitchTypes: { 'fast': '#FF5252', 'breaking': '#2196F3', 'off-speed': '#4CAF50' },
    grid: { scatter: '#1976D2', rolling: '#9C27B0' },
    axis: { scatter: '#1976D2', rolling: '#9C27B0' },
    cursor: '#FF6B35',
    strokeWidth: 4,
    axisStyle: { fontSize: 14, fontWeight: 700, fill: '#1976D2' },
    gridWidth: 2,
    dotStroke: '#333',
    dotStrokeWidth: 2,
  },
  modern: {
    models: ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'],
    pitchTypes: { 'fast': '#ef4444', 'breaking': '#3b82f6', 'off-speed': '#10b981' },
    grid: { scatter: '#e2e8f0', rolling: '#e2e8f0' },
    axis: { scatter: '#94a3b8', rolling: '#94a3b8' },
    cursor: '#94a3b8',
    strokeWidth: 2.5,
    axisStyle: { fontSize: 12, fontWeight: 500, fill: '#64748b' },
    gridWidth: 1,
    dotStroke: '#fff',
    dotStrokeWidth: 1.5,
  },
}

// Keep backward-compatible defaults
const MODEL_COLORS = THEME_PALETTES.backyard.models
const PITCH_TYPE_COLORS = THEME_PALETTES.backyard.pitchTypes

const MODEL_DESCRIPTIONS = {
  'Transformer': {
    title: 'PitchGPT Transformer',
    description: 'A small GPT-style causal transformer that predicts the next pitch type from the sequence of previous pitches in a game. Like a language model, it treats each pitch as a "token" and learns sequential patterns — what pitchers tend to throw after specific sequences. It also conditions on game context: the count (balls/strikes), outs, and inning.',
    details: '6-layer transformer, 4 attention heads, ~800K parameters. Trained on Statcast data with a 5-minute time budget.',
  },
  'Naive (Always Fast)': {
    title: 'Naive (Always Fast)',
    description: 'Always predicts "fast". A baseline that exploits the class imbalance — since ~56% of pitches are fastballs, this simple strategy is surprisingly competitive.',
    details: 'No parameters. Zero training required.',
  },
  'N-Gram (n=3)': {
    title: 'N-Gram (n=3)',
    description: 'An adaptation of Aaronson\'s Oracle for pitch prediction. Tracks the last 3 pitch types as a "context" and predicts whatever pitch type most frequently followed that context within the current game. Builds its lookup table on-the-fly.',
    details: 'Online learning — adapts to each pitcher\'s tendencies during the game.',
  },
  'Markov Context': {
    title: 'Markov Context',
    description: 'Extends the n-gram approach by conditioning on game state (count and outs) in addition to recent pitch history. Tracks pitch patterns within specific game situations — e.g., what a pitcher tends to throw in a 3-2 count with 2 outs.',
    details: 'Online learning with situational context awareness.',
  },
}

function ModelComparison({ predictions, theme = 'backyard' }) {
  const { player_name, game_date, home_team, away_team, pitcher_team, total_pitches, pitch_types_distribution, actual_pitches, models } = predictions
  const descriptionsRef = useRef(null)
  const palette = THEME_PALETTES[theme] || THEME_PALETTES.backyard

  // Lift over the naive (always-fast) baseline. Surfaces where models actually
  // add value (junk-ballers) vs where naive is unbeatable (fastball-heavy).
  const naiveModel = models.find(m => m.model_name === 'Naive (Always Fast)')
  const naiveAccuracy = naiveModel ? naiveModel.accuracy : null
  const liftFor = (model) => (naiveAccuracy == null || model.model_name === 'Naive (Always Fast)') ? null : model.accuracy - naiveAccuracy
  const formatLift = (lift) => {
    if (lift == null) return null
    const pct = (lift * 100).toFixed(1)
    return lift >= 0 ? `+${pct}%` : `${pct}%`
  }

  const scrollToModel = (modelName) => {
    const el = document.getElementById(`model-desc-${modelName.replace(/[^a-zA-Z0-9]/g, '-')}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

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

      {naiveAccuracy != null && (() => {
        const others = models.filter(m => m.model_name !== 'Naive (Always Fast)')
        if (others.length === 0) return null
        const best = others.reduce((a, b) => (a.accuracy >= b.accuracy ? a : b))
        const lift = best.accuracy - naiveAccuracy
        const verdict = lift > 0.02
          ? `${best.model_name} beats the always-fast baseline by ${formatLift(lift)} on this game.`
          : lift < -0.02
            ? `On this game, no model beats the always-fast baseline (${formatLift(lift)}). Likely a fastball-heavy outing.`
            : `Models are roughly tied with the always-fast baseline (${formatLift(lift)}). Naive is hard to beat here.`
        return (
          <div className={`lift-banner ${lift > 0.02 ? 'positive' : lift < -0.02 ? 'negative' : 'neutral'}`}>
            <span className="lift-banner-label">Lift over Naive</span>
            <span className="lift-banner-value">{verdict}</span>
          </div>
        )
      })()}

      <div className="pitch-predictions-chart">
        <h3>Pitch Predictions vs Actual</h3>
        <ResponsiveContainer width="100%" height={200 + models.length * 40}>
          <ScatterChart margin={{ top: 20, right: 100, bottom: 50, left: 150 }}>
            <CartesianGrid strokeDasharray="5 5" stroke={palette.grid.scatter} strokeWidth={palette.gridWidth} horizontal={false} />
            <XAxis
              type="number"
              dataKey="pitch"
              name="Pitch Number"
              domain={[1, total_pitches]}
              tick={palette.axisStyle}
              tickCount={10}
              stroke={palette.axis.scatter}
              strokeWidth={palette.gridWidth + 1}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Model"
              domain={[0, models.length + 1]}
              ticks={[models.length + 0.5, ...models.map((_, i) => models.length - i - 0.5)]}
              tick={palette.axisStyle}
              tickFormatter={(value) => {
                if (value === models.length + 0.5) return 'Actual'
                const modelIndex = models.length - Math.ceil(value)
                return models[modelIndex]?.model_name || ''
              }}
              stroke={palette.axis.scatter}
              strokeWidth={palette.gridWidth + 1}
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3', stroke: palette.cursor, strokeWidth: 2 }}
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div className="chart-tooltip">
                      <p style={{ margin: 0, fontWeight: 800, marginBottom: '4px', fontSize: '1rem' }}>Pitch #{data.pitch}</p>
                      <p style={{ margin: 0, fontWeight: 600 }}>{data.label}: <span style={{ color: palette.pitchTypes[data.pitchType], fontWeight: 800 }}>{data.pitchType}</span></p>
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
                    <span className="legend-dot" style={{ backgroundColor: palette.pitchTypes.fast }}></span>
                    <span>Fast</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot" style={{ backgroundColor: palette.pitchTypes.breaking }}></span>
                    <span>Breaking</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-dot" style={{ backgroundColor: palette.pitchTypes['off-speed'] }}></span>
                    <span>Off-Speed</span>
                  </div>
                </div>
              )}
            />
            <Scatter data={pitchScatterData} shape="circle">
              {pitchScatterData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={palette.pitchTypes[entry.pitchType]}
                  stroke={palette.dotStroke}
                  strokeWidth={palette.dotStrokeWidth}
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
            <CartesianGrid strokeDasharray="5 5" stroke={palette.grid.rolling} strokeWidth={palette.gridWidth} horizontal={false} />
            <XAxis
              type="number"
              dataKey="pitch"
              domain={[1, total_pitches]}
              tick={palette.axisStyle}
              tickCount={10}
              stroke={palette.axis.rolling}
              strokeWidth={palette.gridWidth + 1}
            />
            <YAxis
              domain={[0, 1]}
              tick={palette.axisStyle}
              tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
              stroke={palette.axis.rolling}
              strokeWidth={palette.gridWidth + 1}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="chart-tooltip">
                      <p style={{ margin: 0, fontWeight: 800, marginBottom: '6px', fontSize: '1rem' }}>Pitch #{label}</p>
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
              content={() => (
                <div className="rolling-legend">
                  {models.map((model, index) => (
                    <span
                      key={model.model_name}
                      className="rolling-legend-item"
                      onClick={() => scrollToModel(model.model_name)}
                    >
                      <span
                        className="rolling-legend-line"
                        style={{ backgroundColor: palette.models[index % palette.models.length] }}
                      />
                      {model.model_name}
                    </span>
                  ))}
                </div>
              )}
            />
            {models.map((model, index) => (
              <Line
                key={model.model_name}
                type="monotone"
                dataKey={model.model_name}
                stroke={palette.models[index % palette.models.length]}
                dot={false}
                strokeWidth={palette.strokeWidth}
                name={model.model_name}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="model-descriptions" ref={descriptionsRef}>
        <h3>About the Models</h3>
        <p className="model-descriptions-subtitle">Click a model name in the chart legend to jump here</p>
        <div className="model-cards-grid">
          {models.map((model, index) => {
            const info = MODEL_DESCRIPTIONS[model.model_name]
            if (!info) return null
            return (
              <div
                key={model.model_name}
                id={`model-desc-${model.model_name.replace(/[^a-zA-Z0-9]/g, '-')}`}
                className="model-card"
                style={{ borderLeftColor: palette.models[index % palette.models.length] }}
              >
                <div className="model-card-header">
                  <h4 style={{ color: palette.models[index % palette.models.length] }}>{info.title}</h4>
                  <div className="model-card-metrics">
                    <span className="model-card-accuracy">{(model.accuracy * 100).toFixed(1)}%</span>
                    {liftFor(model) != null && (
                      <span className={`model-card-lift ${liftFor(model) >= 0 ? 'positive' : 'negative'}`}>
                        {formatLift(liftFor(model))} vs naive
                      </span>
                    )}
                  </div>
                </div>
                <p className="model-card-description">{info.description}</p>
                <p className="model-card-details">{info.details}</p>
              </div>
            )
          })}
        </div>
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
  theme: PropTypes.oneOf(['backyard', 'modern']),
}

export default ModelComparison
