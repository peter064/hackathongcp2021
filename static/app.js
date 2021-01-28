// From: https://developer.mozilla.org/en-US/docs/Web/API/MediaStream_Recording_API/Using_the_MediaStream_Recording_API
// Source: https://github.com/mdn/web-dictaphone/blob/gh-pages/scripts/app.js

// set up basic variables for app

const record = document.querySelector('.record');
const stop = document.querySelector('.stop');
const canvas = document.querySelector('.visualizer');
const mainSection = document.querySelector('.main-controls');


// disable stop button while not recording

stop.disabled = true;

// visualiser setup - create web audio api context and canvas

let audioCtx;
const canvasCtx = canvas.getContext("2d");

//main block for doing the audio recording

if (navigator.mediaDevices.getUserMedia) {
  console.log('getUserMedia supported.');

  const constraints = { audio: true };
  let chunks = [];

  let onSuccess = function(stream) {
    const mediaRecorder = new MediaRecorder(stream);

    visualize(stream);

    record.onclick = function() { // from https://github.com/dialogflow/selfservicekiosk-audio-streaming/blob/master/examples/example5.html
        var triggerWord = document.getElementById("triggerWord").value;
        var webhookUrl = document.getElementById("webhookUrl").value;
        navigator.getUserMedia({
            audio: true
        }, function(stream) {
                recordAudio = RecordRTC(stream, {
                type: 'audio',
                mimeType: 'audio/webm',
                sampleRate: 44100, // this sampleRate should be the same in your server code

                // MediaStreamRecorder, StereoAudioRecorder, WebAssemblyRecorder
                // CanvasRecorder, GifRecorder, WhammyRecorder
                recorderType: StereoAudioRecorder,

                // Dialogflow / STT requires mono audio
                numberOfAudioChannels: 1,

                // get intervals based blobs
                // value in milliseconds
                // as you might not want to make detect calls every seconds
                timeSlice: 5000,

                // only for audio track
                // audioBitsPerSecond: 128000,

                // used by StereoAudioRecorder
                // the range 22050 to 96000.
                // let us force 16khz recording:
                desiredSampRate: 16000,

                // as soon as the stream is available
                ondataavailable: function(blob) {
                    // making use of socket.io-stream for bi-directional
                    // streaming, create a stream
                    console.log("got data")
                    // var stream = ss.createStream();
                    // stream directly to server
                    // it will be temp. stored locally
                    console.log("emitting data to socket")
                    // ss(socket).emit('stream-transcribe', stream, {
                    //     name: 'stream.wav', 
                    //     size: blob.size
                    // });
                    socket.emit('audio_chunk', blob, triggerWord, webhookUrl);
                    // pipe the audio blob to the read stream
                    // ss.createBlobReadStream(blob).pipe(stream);
                }
            });
            socket.emit('settings', {"trigger_word": triggerWord, "webhook_url": webhookUrl})
            recordAudio.startRecording();
            stop.disabled = false;
            record.disabled = true;
        }, function(error) {
            console.error(JSON.stringify(error));
        });
      console.log("recorder started");
    }

    stop.onclick = function() {
        recordAudio.stopRecording();
        stop.disabled = true;
        record.disabled = false;
    }
  }

  let onError = function(err) {
    console.log('The following error occured: ' + err);
  }

  navigator.mediaDevices.getUserMedia(constraints).then(onSuccess, onError);

} else {
   console.log('getUserMedia not supported on your browser!');
}

function visualize(stream) {
  if(!audioCtx) {
    audioCtx = new AudioContext();
  }

  const source = audioCtx.createMediaStreamSource(stream);

  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 2048;
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  source.connect(analyser);
  //analyser.connect(audioCtx.destination);

  draw()

  function draw() {
    const WIDTH = canvas.width
    const HEIGHT = canvas.height;

    requestAnimationFrame(draw);

    analyser.getByteTimeDomainData(dataArray);

    canvasCtx.fillStyle = 'rgb(200, 200, 200)';
    canvasCtx.fillRect(0, 0, WIDTH, HEIGHT);

    canvasCtx.lineWidth = 2;
    canvasCtx.strokeStyle = 'rgb(0, 0, 0)';

    canvasCtx.beginPath();

    let sliceWidth = WIDTH * 1.0 / bufferLength;
    let x = 0;


    for(let i = 0; i < bufferLength; i++) {

      let v = dataArray[i] / 128.0;
      let y = v * HEIGHT/2;

      if(i === 0) {
        canvasCtx.moveTo(x, y);
      } else {
        canvasCtx.lineTo(x, y);
      }

      x += sliceWidth;
    }

    canvasCtx.lineTo(canvas.width, canvas.height/2);
    canvasCtx.stroke();

  }
}

window.onresize = function() {
  canvas.width = mainSection.offsetWidth;
}

window.onresize();