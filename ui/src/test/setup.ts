import '@testing-library/jest-dom/vitest'

// jsdom has no canvas; the globe loader simply skips drawing when the
// 2D context is unavailable.
HTMLCanvasElement.prototype.getContext = (() => null) as typeof HTMLCanvasElement.prototype.getContext
