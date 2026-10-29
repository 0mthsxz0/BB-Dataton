$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$sintetizador = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $sintetizador.SelectVoice('Microsoft Maria Desktop')
    $formato = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $sintetizador.SetOutputToWaveFile($env:BB_AUDIO_DESTINO, $formato)
    $texto = [System.IO.File]::ReadAllText($env:BB_AUDIO_TEXTO, [System.Text.Encoding]::UTF8)
    $sintetizador.Speak($texto)
} finally {
    $sintetizador.Dispose()
}
