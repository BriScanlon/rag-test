// logHelper.js
import log from 'loglevel';

// Set log level dynamically based on environment variable (defaults to 'info')
const logLevel = import.meta.env.VITE_LOG_LEVEL || 'info';
log.setLevel(logLevel);

const logHelper = {
  info: (message, ...args) => log.info(message, ...args),
  warn: (message, ...args) => log.warn(message, ...args),
  error: (message, ...args) => log.error(message, ...args),
  debug: (message, ...args) => log.debug(message, ...args),
};

export default logHelper;
