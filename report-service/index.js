const { createApp } = require('./lib/app')

const PORT = process.env.PORT || 3001

createApp().listen(PORT, () => {
  console.log(`Report service listening on port ${PORT}`)
})
