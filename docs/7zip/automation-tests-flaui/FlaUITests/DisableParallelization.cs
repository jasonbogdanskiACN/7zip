// Ensures all FlaUI tests in this assembly run sequentially.
// Without this, 3 separate 7zFM.exe instances receive interleaved mouse/keyboard
// SendInput events, causing each test to send keystrokes to the wrong window.

using Xunit;

[assembly: CollectionBehavior(DisableTestParallelization = true)]
