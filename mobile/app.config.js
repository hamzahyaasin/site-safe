// Adds Firebase configuration to Android builds when google-services.json is
// present. Push alerts need it (the backend sends through FCM); without it
// the app still builds and receives alerts live while open.
const fs = require('fs')
const path = require('path')

module.exports = ({ config }) => {
  // eslint-disable-next-line no-undef -- Node config file
  const googleServices = path.join(__dirname, 'google-services.json')
  if (fs.existsSync(googleServices)) {
    config.android = { ...config.android, googleServicesFile: './google-services.json' }
  }
  return config
}
