"""v3 depth for the settings domain (lane C, 2026-10-04). Facts are the ones already sourced in the articles (paint-booth-v2.html settings drop-down, js/spb-native-file-dialogs.js, electron-app licence files)."""
V3 = {
 'settings.overview': {
  'level': 'beginner',
  'deep': [
   {'heading': 'The drop-down from top to bottom',
    'body': 'License shows your licence status. LOOKS changes the theme of the booth. Options holds Export ZIP Package, Training Wheels, the dark/light toggle, the File Picker choice and Report a Problem. Quick Tools holds Keyboard Shortcuts. Import Spec Map merges an existing shine file under your zones, with a Clear button. Auto-Deploy to iRacing copies each render into your car folder. Everything is remembered on this computer.'},
   {'heading': 'Two different gears',
    'body': 'The gear at the top right is the booth settings. The AI panel has its own gear, which holds the AI key, the model and the Claude or ChatGPT connection. Mixing them up is the most common reason people cannot find the key box.'},
   {'heading': 'Settings that change your files, and settings that do not',
    'body': 'Looks, light/dark, File Picker and Training Wheels only change how the booth behaves. Three options touch your output: Export ZIP Package adds a ZIP with the paint TGA, spec TGA and preview on every render; Auto-Deploy copies each render into your iRacing car folder; and an imported spec map stays under every render until you press Clear.'}],
  'examples': [
   {'title': 'Safe experimenting setup', 'goal': 'Try ideas without overwriting a paint you like in iRacing',
    'settings': {'Auto-Deploy to iRacing': 'Off', 'Export ZIP Package': 'On', 'Training Wheels': 'Your choice'},
    'result': 'Every render is bundled in a ZIP in your output folder, and nothing is copied into iRacing until you switch Auto-Deploy on.'},
   {'title': 'Ready to race', 'goal': 'Get each finished render straight into the sim',
    'settings': {'Auto-Deploy to iRacing': 'On', 'iRacing Car Folder': 'Set to your car folder', 'After render': 'Press Ctrl+R in the sim'},
    'result': 'The render lands in the car folder and the sim reloads the car textures.'}],
  'faq': [
   {'q': 'Where is the key box for the AI?', 'a': 'In the gear inside the AI panel, not in the booth Settings gear.'},
   {'q': 'Are my settings saved?', 'a': 'Yes, on this computer. A different computer starts with the defaults.'},
   {'q': 'Does Report a Problem send anything?', 'a': 'No. It copies a report for you to paste to support, and the report never includes your licence key.'},
   {'q': 'Why is there an old spec showing in every render?', 'a': 'You imported a spec map. It stays under every render until you press Clear next to Import Spec Map.'}],
  'mistakes': [
   {'symptom': 'Your iRacing paint was overwritten by an experiment', 'cause': 'Auto-Deploy was on while you were testing', 'fix': 'Turn Auto-Deploy off while experimenting and on when you are happy.'},
   {'symptom': 'Every render has a strange shine you did not set', 'cause': 'An imported spec map is still merged under your zones', 'fix': 'Open Settings and press Clear beside Import Spec Map, then render again.'}],
  'protips': ['Turn on Export ZIP Package for a project you care about. Each render then leaves you a dated bundle of paint, spec and preview to go back to.'],
 },
 'settings.file_picker': {
  'level': 'beginner',
  'deep': [
   {'heading': 'What each chooser gives you',
    'body': 'Shokker Browser is the default. It shows image previews, which is handy for TGA artwork you cannot recognise by name. Windows File Explorer opens the standard Windows chooser, where you can type or paste a path or browse to another drive. It is used for Source Paint, Open Layered and the iRacing Folder button.'},
   {'heading': 'Why it also works in a browser tab',
    'body': 'The booth\'s server runs on your own PC, so even in a browser tab it can open the real Windows dialog for you. The choice is saved on this computer.'},
   {'heading': 'What it does not change',
    'body': 'The picker only changes how you choose a file. Your files, the render and the colours are identical either way.'}],
  'examples': [
   {'title': 'Use a network or second drive', 'goal': 'Open artwork that lives on another drive',
    'settings': {'Settings gear': 'Options', 'File Picker': 'Windows File Explorer', 'Then': 'Click Source Paint and browse or paste the path'},
    'result': 'The Windows chooser opens, and you can type the full path to the file.'},
   {'title': 'Go back to previews', 'goal': 'See image thumbnails while picking TGA artwork',
    'settings': {'Settings gear': 'Options', 'File Picker': 'Shokker Browser'},
    'result': 'The next file chooser shows image previews.'}],
  'faq': [
   {'q': 'The Windows chooser did not appear. Where is it?', 'a': 'It may have opened behind the booth window. Press Alt+Tab to find it.'},
   {'q': 'I cannot find my folder in the Shokker Browser.', 'a': 'Switch to Windows File Explorer and type or paste the path, or browse to the other drive.'},
   {'q': 'Does it change my files?', 'a': 'No. It changes only how you pick them.'}],
  'mistakes': [
   {'symptom': 'You click Source Paint and nothing seems to open', 'cause': 'The Windows chooser opened behind the booth', 'fix': 'Press Alt+Tab, or switch the File Picker back to Shokker Browser.'},
   {'symptom': 'Your network drive is not listed', 'cause': 'The Shokker Browser does not show every drive', 'fix': 'Use Windows File Explorer and paste the path.'}],
  'protips': ['If you are going to open many TGA files in a row, keep the Shokker Browser. Previews save you from opening the wrong file.'],
 },
 'settings.looks_training_wheels': {
  'level': 'beginner',
  'deep': [
   {'heading': 'Sixteen looks, all instant',
    'body': 'Classic Mode is the default, and 15 more looks are Pro Dark, Linear, Nord, Dracula, Monokai, Solarized Dark, Carbon, OLED Black, Graphite, Studio Warm, Midnight Navy, Emerald Pro, Copper, High Contrast and Compact Pro. Switching applies at once and is remembered. A Light button switches between dark and light. None of it changes your paint, only the colours and shapes of the booth.'},
   {'heading': 'Retired looks',
    'body': 'The white modes (Pro Light, Paper, Spacious) were retired. If you saved one of them earlier, the booth falls back to Classic instead of breaking.'},
   {'heading': 'Training Wheels',
    'body': 'Training Wheels is the switch for step-by-step quests and a next-move hint chip that teach the app while you work. Finishing the Core Loop offers to turn it off. It is off until you choose to turn it on.'}],
  'examples': [
   {'title': 'Easier on the eyes', 'goal': 'Make the booth readable on a hard-to-read monitor',
    'settings': {'LOOKS': 'High Contrast', 'Light button': 'Try it if the screen is bright'},
    'result': 'High Contrast is the easiest look to read.'},
   {'title': 'More room for the car', 'goal': 'Fit more on a small screen',
    'settings': {'LOOKS': 'Compact Pro'},
    'result': 'Tighter panels leave more room for the preview.'}],
  'faq': [
   {'q': 'Does a look change my paint?', 'a': 'No. It only changes the booth\'s colours and shapes.'},
   {'q': 'How do I get rid of the hints?', 'a': 'Switch Training Wheels off in Options, or finish the Core Loop and accept the offer to turn it off.'},
   {'q': 'The booth looks cramped.', 'a': 'Try Compact Pro, or change the UI size in the panels settings.'},
   {'q': 'My saved look disappeared.', 'a': 'If it was one of the retired white modes, the booth fell back to Classic. Pick another look.'}],
  'mistakes': [
   {'symptom': 'You look for a white theme and cannot find it', 'cause': 'The white modes were retired', 'fix': 'Use the Light button next to LOOKS for a light theme.'},
   {'symptom': 'Hints keep popping up', 'cause': 'Training Wheels is on', 'fix': 'Turn it off in Settings, Options.'}],
  'protips': ['Pick the look first, then the UI size. A look that fits your monitor saves more eye strain than any other setting.'],
 },
 'settings.activation_license': {
  'level': 'beginner',
  'deep': [
   {'heading': 'What happens at start-up',
    'body': 'The licence window asks for your key. The app checks it with the seller\'s licence service and, if it is good, saves an encrypted licence file for this computer. If the service cannot be reached, it saves an offline activation instead and lets you in.'},
   {'heading': 'Tied to the PC and the Windows user',
    'body': 'A saved licence works for this PC and this Windows user. Reinstalling Windows on the same account does not need a new key. A different PC, or a changed Windows account, asks for the key again.'},
   {'heading': 'Moving to a new PC',
    'body': 'Use Deactivate on the old PC if you can, so the key is free. If the new PC refuses the key as already used, contact support and say which PC the key was used on.'},
   {'heading': 'What Settings shows afterwards',
    'body': 'In current builds the gear shows License Active and hides the key box, because activation already happened at start-up.'}],
  'examples': [
   {'title': 'First start after installing', 'goal': 'Activate the app',
    'settings': {'Key': 'Paste it without extra spaces', 'Button': 'Activate', 'Wait': 'Verifying'},
    'result': 'The app opens. If your internet is down it says it saved an offline activation.'},
   {'title': 'Switch to a new PC', 'goal': 'Use the same key on a new computer',
    'settings': {'Old PC': 'Deactivate (if you still can)', 'New PC': 'Enter the same key at start-up'},
    'result': 'The key activates on the new PC. If refused as already used, contact support.'}],
  'faq': [
   {'q': 'Can I work offline?', 'a': 'Yes once activated. If the licence service cannot be reached at activation, the app saves an offline activation.'},
   {'q': 'Why does it ask for my key again?', 'a': 'You are on a different PC or Windows account, or the saved licence file was removed.'},
   {'q': 'Where do I buy a key?', 'a': 'The same licence window has a Buy License button.'},
   {'q': 'Is my key included in a problem report?', 'a': 'No. Report a Problem never includes it.'}],
  'mistakes': [
   {'symptom': 'The key is refused', 'cause': 'A typo or extra spaces when pasting', 'fix': 'Copy it again from your receipt and paste without spaces.'},
   {'symptom': 'You post a screenshot with your key in it', 'cause': 'The key is visible in the licence window', 'fix': 'Never share the key. Hide it before sending screenshots.'}],
  'protips': ['Keep the email or receipt with your key somewhere safe. It is the only way to reactivate on a new PC.'],
 },
}
