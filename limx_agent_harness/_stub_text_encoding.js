module.exports = {
  TextEncoder: typeof TextEncoder !== 'undefined' ? TextEncoder : require('util').TextEncoder,
  TextDecoder: typeof TextDecoder !== 'undefined' ? TextDecoder : require('util').TextDecoder
};
