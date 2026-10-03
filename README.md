# Spatial Audio Lab

Spatial Audio Lab on Pythonilla tehty reaaliaikainen spatial audio -ohjelma.

Ohjelmassa voit sijoittaa virtuaalisen kaiutinparin henkilön ympärille ja kuunnella, miltä ääni kuulostaa eri suunnista ja etäisyyksiltä.

## Ominaisuudet

* MP3
* WAV
* FLAC
* OGG
* M4A
* AAC
* Opus
* Stereo / binauraalinen spatial audio
* Vasen/oikea voimakkuusero
* ITD (Interaural Time Difference)
* Head shadow -mallinnus
* Etäisyyteen perustuva äänen vaimeneminen
* 0–80 äänenvoimakkuusasteikko
* Kaiuttimen raahaaminen hiirellä
* Etäisyyden syöttäminen metreinä
* Kulman syöttäminen asteina
* Play
* Pause
* Stop
* Repeat
* 10 animaatiota
* Animaation nopeus 0.05×–20×
* Reaaliaikaiset spatial audio -tiedot

---

# Vaatimukset

## Python

Suositeltu Python-versio:

```text
Python 3.10+
```

Python 3.12 toimii.

Tarkista Python:

```powershell
py --version
```

## Python-kirjastot

Asenna tarvittavat kirjastot:

```powershell
py -m pip install numpy sounddevice
```

Ohjelma käyttää:

* `tkinter` – käyttöliittymä
* `numpy` – audiodatan käsittely
* `sounddevice` – äänen toisto

---

# FFmpeg

Spatial Audio Lab käyttää FFmpegia audiotiedostojen purkamiseen.

## FFmpeg pitää olla PATHissa

**FFmpeg täytyy olla lisättynä Windowsin PATH-ympäristömuuttujaan.**

Ohjelma käynnistää FFmpegin suoraan komennolla:

```text
ffmpeg
```

Tarkista, että FFmpeg löytyy:

```powershell
ffmpeg -version
```

Jos komento näyttää FFmpegin version, FFmpeg on PATHissa oikein.

Esimerkiksi:

```text
ffmpeg version ...
configuration: ...
libavcodec ...
libavformat ...
```

Jos saat virheen kuten:

```text
'ffmpeg' is not recognized as the name of a cmdlet,
function, script file, or operable program.
```

FFmpeg ei ole PATHissa.

## FFmpeg-kansion rakenne

FFmpeg-kansiossa pitäisi olla esimerkiksi:

```text
ffmpeg
└── bin
    ├── ffmpeg.exe
    ├── ffplay.exe
    └── ffprobe.exe
```

Jos kansio on esimerkiksi:

```text
C:\ffmpeg\bin
```

PATHiin lisätään:

```text
C:\ffmpeg\bin
```

Sen jälkeen avaa uusi PowerShell tai Command Prompt.

Testaa:

```powershell
ffmpeg -version
```

### Miksi PATH tarvitaan?

Spatial Audio Lab ei käytä FFmpegia Python-kirjastona.

Python käynnistää `ffmpeg.exe`:n ohjelmana:

```text
Python
  ↓
ffmpeg.exe
  ↓
Audio
  ↓
Spatial Audio Lab
```

Siksi `ffmpeg`-komennon täytyy toimia suoraan PowerShellissä.

---

# Käynnistys

Tallenna ohjelma esimerkiksi nimellä:

```text
spatial_audio_lab.py
```

Käynnistä:

```powershell
py spatial_audio_lab.py
```

---

# Käyttö

## OPEN AUDIO

Avaa audiotiedoston.

Tuetut formaatit:

```text
MP3
WAV
FLAC
OGG
M4A
AAC
Opus
```

Audio dekoodataan FFmpegillä ohjelman sisäiseen muotoon:

```text
Mono
48000 Hz
float32
```

---

# Playback

## PLAY

Käynnistää toiston.

## PAUSE

Keskeyttää toiston.

PLAY jatkaa samasta kohdasta.

## STOP

Pysäyttää toiston ja siirtää kappaleen alkuun.

## Once

Kappale soi kerran.

Kun kappale loppuu, toisto pysähtyy.

## Repeat

Kappale aloitetaan automaattisesti uudelleen sen loputtua.

---

# Volume

Äänenvoimakkuuden asteikko on:

```text
0–80
```

Esimerkiksi:

```text
80 = täysi taso
70 = noin -10 dB
60 = noin -20 dB
50 = noin -30 dB
```

Arvon voi säätää sliderilla tai kirjoittaa kenttään.

---

# Speaker position

Virtuaalinen kaiutinpari näkyy kartalla.

Kaiutinta voi liikuttaa hiirellä:

1. Vie hiiri kaiuttimen päälle.
2. Paina hiiren vasenta painiketta.
3. Raahaa kaiutin haluttuun paikkaan.
4. Vapauta hiiren painike.

Raahaaminen vaihtaa animaation automaattisesti manuaaliseksi.

---

# Koordinaatisto

Henkilö on keskellä.

```text
                 FRONT
                   0°
                   ↑
                   |
                   |
       -90°  ←    ●    →  +90°
                   |
                   |
                   ↓
                 BACK
                  180°
```

Kulmat:

```text
0°     = edessä
+90°   = oikealla
180°   = takana
-90°   = vasemmalla
```

---

# Distance

Distance määrittää kaiuttimen etäisyyden henkilöstä.

Esimerkiksi:

```text
1.0 m
2.0 m
5.0 m
10.0 m
```

Mitä kauempana lähde on, sitä hiljaisemmaksi ääni muuttuu.

---

# Angle

Angle määrittää suunnan.

Esimerkiksi:

```text
0°
```

Kaiutin on suoraan edessä.

```text
90°
```

Kaiutin on oikealla.

```text
-90°
```

Kaiutin on vasemmalla.

```text
180°
```

Kaiutin on takana.

---

# Spatial Audio

Spatial Audio Lab käyttää useita ihmisen kuuloon liittyviä vihjeitä.

## ILD / voimakkuusero

Lähempänä oleva korva saa voimakkaamman äänen.

Esimerkiksi oikealla olevan lähteen tapauksessa:

```text
RIGHT = voimakkaampi
LEFT  = heikompi
```

---

## ITD

ITD tarkoittaa:

```text
Interaural Time Difference
```

Ääni saapuu toiselle korvalle hieman aikaisemmin kuin toiselle.

Ohjelma simuloi tätä viivästyttämällä toista stereokanavaa näytteillä.

---

## Head Shadow

Pää vaimentaa ääntä, kun lähde on voimakkaasti toisella puolella päätä.

Ohjelma käyttää tästä yksinkertaistettua mallia.

---

## Distance Attenuation

Äänen voimakkuus pienenee etäisyyden kasvaessa.

Ohjelmassa käytetään yksinkertaistettua:

```text
1 / distance
```

-vaimennusta.

---

# Animation

Ohjelmassa on 10 animaatiota.

## 1. Manuaalinen

Kaiutinta ohjataan itse hiirellä.

---

## 2. Orbit 1 m

Kaiutin kiertää henkilöä yhden metrin säteellä.

---

## 3. Orbit 2 m

Kaiutin kiertää henkilöä kahden metrin säteellä.

---

## 4. Orbit 5 m

Kaiutin kiertää henkilöä viiden metrin säteellä.

---

## 5. Orbit 10 m

Kaiutin kiertää henkilöä kymmenen metrin säteellä.

---

## 6. Orbit Custom

Käyttäjä voi määrittää oman kiertosäteen.

Esimerkiksi:

```text
3.0
```

tarkoittaa kolmen metrin kiertorataa.

---

## 7. Vasen → Oikea

Kaiutin liikkuu vasemmalta oikealle ja takaisin.

---

## 8. Eteen → Taakse

Kaiutin liikkuu henkilön edestä taakse ja takaisin.

---

## 9. Kahdeksikko

Kaiutin liikkuu kahdeksikon muotoisella radalla.

```text
       ╭────╮
      ╱      ╲
      ╲      ╱
       ╰────╯
```

---

## 10. Satunnainen

Kaiutin liikkuu satunnaisiin paikkoihin henkilön ympärillä.

---

# Animation Speed

Animaation nopeutta voidaan säätää:

```text
0.05×–20×
```

Esimerkkejä:

```text
0.05× = erittäin hidas
0.5×  = puolet normaalista
1.0×  = normaali
2.0×  = kaksi kertaa nopeampi
5.0×  = erittäin nopea
10×   = erittäin nopea
20×   = maksimaalinen nopeus
```

Nopeutta voi säätää sliderilla tai kirjoittamalla arvon kenttään.

Esimerkiksi:

```text
2.5
```

tarkoittaa 2.5× nopeutta.

---

# Reaaliaikaiset tiedot

Kartan alapuolella näytetään:

```text
DISTANCE
ANGLE
ITD
LEFT GAIN
RIGHT GAIN
DISTANCE GAIN
```

Esimerkiksi:

```text
DISTANCE       2.83 m
ANGLE          35.3°
ITD            12 samples
LEFT GAIN      0.72
RIGHT GAIN     1.00
DISTANCE GAIN  0.353
```

---

# Audio processing

Audio käsitellään seuraavasti:

```text
Audio file
    ↓
FFmpeg
    ↓
Mono
    ↓
48 kHz float32
    ↓
Spatial positioning
    ↓
ITD
    ↓
Left/right level difference
    ↓
Head shadow
    ↓
Distance attenuation
    ↓
Master volume
    ↓
Stereo
    ↓
sounddevice
    ↓
Audio device
```

---

# Tekniset asetukset

Oletusasetukset:

```text
Sample rate:       48000 Hz
Block size:        256 samples
Channels:          2
Format:            float32
Speed of sound:    343 m/s
Ear distance:      0.175 m
Maximum distance:  20 m
```

---

# Rajoitukset

Spatial Audio Lab käyttää tällä hetkellä yksinkertaistettua spatial audio -mallia.

Se ei vielä ole täydellinen HRTF-simulaatio.

Erityisesti:

* etu- ja takasuunnan erottelu ei ole täydellistä
* korvalehden vaikutusta ei vielä simuloida tarkasti
* huoneen heijastuksia ei simuloida
* kaiuntaa ei simuloida
* Doppler-efektiä ei vielä ole
* ympäristön akustiikkaa ei simuloida
* lähde on tällä hetkellä yksi monoäänilähde

Tarkempaan binauraaliseen spatial audioon tarvittaisiin esimerkiksi HRTF-dataa.

---

# Mahdollisia tulevia ominaisuuksia

* HRTF-tuki
* oikeat ihmiskorvien impulssivasteet
* parempi etu/taka-erottelu
* korvalehden simulointi
* huoneakustiikka
* seinien heijastukset
* reverb
* low-pass head shadow
* Doppler-efekti
* useita samanaikaisia äänilähteitä
* useita kuuntelijoita
* 3D-näkymä
* waveform
* audio timeline
* BPM-synkronoidut animaatiot
* MIDI-ohjaus
* OSC-ohjaus
* HRTF-tiedostojen lataaminen
* kuulokkeille optimoitu binauraalinen tila

---

# Projektin rakenne

Yksinkertainen versio koostuu kahdesta tiedostosta:

```text
SpatialAudioLab/
│
├── spatial_audio_lab.py
└── README.md
```

---

# Asennus nopeasti

Asenna Python-kirjastot:

```powershell
py -m pip install numpy sounddevice
```

Tarkista FFmpeg:

```powershell
ffmpeg -version
```

Jos FFmpeg-komento ei toimi, lisää FFmpegin `bin`-kansio Windowsin PATHiin.

Käynnistä ohjelma:

```powershell
py spatial_audio_lab.py
```

---

# Vianmääritys

## `ffmpeg is not recognized`

FFmpeg ei ole PATHissa.

Tarkista esimerkiksi:

```powershell
where.exe ffmpeg
```

Jos FFmpeg on oikein PATHissa, komennon pitäisi näyttää esimerkiksi:

```text
C:\ffmpeg\bin\ffmpeg.exe
```

---

## `No module named numpy`

Asenna NumPy:

```powershell
py -m pip install numpy
```

---

## `No module named sounddevice`

Asenna SoundDevice:

```powershell
py -m pip install sounddevice
```

---

## Ääntä ei kuulu

Tarkista:

1. Windowsin oletusäänilaite.
2. Että audio on ladattu.
3. Että PLAY on painettu.
4. Että volume ei ole 0.
5. Että FFmpeg toimii.
6. Että ohjelmalla on käytettävissä oleva äänilaite.

Voit testata SoundDevice-laitteet Pythonilla:

```powershell
py -c "import sounddevice as sd; print(sd.query_devices())"
```

---

# Käytetyt teknologiat

* Python
* Tkinter
* NumPy
* SoundDevice
* FFmpeg

---

# Lisenssi

Spatial Audio Lab on tarkoitettu kokeiluun, opiskeluun ja oman spatial audio -järjestelmän kehittämiseen.
