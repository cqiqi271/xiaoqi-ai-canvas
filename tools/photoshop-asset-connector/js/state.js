/* 共享状态 + 本地持久化键。挂到全局 DX 命名空间（多 script 共享作用域）。 */
window.DX = window.DX || {};

DX.LS = {
  host: 'xiaoqi.assets.host',
  source: 'xiaoqi.assets.source',
  exportLayer: 'xiaoqi.assets.exportLayer',
};

DX.state = {
  host: '',
  connected: false,
  tab: 'assets',                 // assets | generate | settings
  source: 'assets',              // assets | canvas | local
  raw: { assets: null, canvas: null, local: null },
  aId: '',
  bId: '',
  selectedId: '',
  exportLayer: false,
  // WebSocket
  ws: null,
  wsPing: null,
  wsBackoff: 1000,
  wsWasOpen: false,
  reconnectTimer: null,
  reloadTimer: null,
};
