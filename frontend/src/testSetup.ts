import '@testing-library/jest-dom';

// jsdom doesn't implement matchMedia — ThemeProvider and useReducedMotion
// both read it, so every component test needs a stub, not just theme tests.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Radix primitives (Dialog/Sheet/Select/DropdownMenu) probe these during
// layout/positioning; jsdom has neither.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false;
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => {};
}
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = () => {};
}
if (typeof window.PointerEvent === 'undefined') {
  class PointerEventPolyfill extends MouseEvent {
    pointerId?: number;
    pointerType?: string;
    constructor(type: string, params: PointerEventInit = {}) {
      super(type, params);
      this.pointerId = params.pointerId;
      this.pointerType = params.pointerType;
    }
  }
  // @ts-expect-error jsdom has no native PointerEvent constructor
  window.PointerEvent = PointerEventPolyfill;
}

// cmdk (the Combobox/Command palette's underlying library) uses
// ResizeObserver to auto-size its list; jsdom has no implementation at all.
if (typeof window.ResizeObserver === 'undefined') {
  class ResizeObserverPolyfill {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.ResizeObserver = ResizeObserverPolyfill;
}

// jsdom has no Blob object-URL implementation at all (BE-076: PDF preview/
// download blob handling needs both).
if (typeof window.URL.createObjectURL === 'undefined') {
  window.URL.createObjectURL = () => 'blob:mock-object-url';
}
if (typeof window.URL.revokeObjectURL === 'undefined') {
  window.URL.revokeObjectURL = () => {};
}

// jsdom's layout engine always returns an all-zero rect. Radix's Popper
// positioning (Popover/Select/DropdownMenu) treats a real, stable, non-zero
// rect as a signal that measurement has settled — with everything stuck at
// zero, its measurement effect never stabilizes and a real click through
// an open popover hangs indefinitely (a genuine jsdom-only livelock, not a
// bug in the component). A fixed plausible size resolves it immediately.
Element.prototype.getBoundingClientRect = () => ({
  width: 120,
  height: 40,
  top: 0,
  left: 0,
  right: 120,
  bottom: 40,
  x: 0,
  y: 0,
  toJSON() {
    return this;
  },
});
