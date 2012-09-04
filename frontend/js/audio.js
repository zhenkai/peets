$(document).ready(function()
{
  createWebSocket();
  getUserMedia();
});

var pc;
var ws;

function createWebSocket()
{
  ws = new WebSocket("ws://127.0.0.1:9000");
  ws.onopen = function(event){ console.log("WebSocket opened."); };
  ws.onmessage = function(event) 
  {
    var message = event.data;
    processSignalingMessage(message);
  };
  ws.onclose = function(event) { console.log("WebSocket closed."); };
  ws.onerror = function(event) { console.log("WebSocket error."); };
}

function getUserMedia() 
{
  try 
  {
    navigator.webkitGetUserMedia({audio:true}, onUserMediaSuccess,
                                 onUserMediaError);
    console.log("Requested access to local media with new syntax.");
  } 
  catch (e) 
  {
    try 
    {
      navigator.webkitGetUserMedia("audio", onUserMediaSuccess,
                                   onUserMediaError);
      console.log("Requested access to local media with old syntax.");
    } 
    catch (e) 
    {
      alert("webkitGetUserMedia() failed. Is the MediaStream flag enabled in about:flags?");
      console.log("webkitGetUserMedia failed with exception: " + e.message);
    }
  }
}

function onUserMediaSuccess(stream) 
{
  console.log("User has granted access to local media.");
  var url = webkitURL.createObjectURL(stream);
  createPeerConnection();
  pc.addStream(stream);
  doCall();
}

function onUserMediaError(error) 
{
  console.log("Failed to get access to local media. Error code was " + error.code);
  alert("Failed to get access to local media. Error code was " + error.code + ".");
}

function createPeerConnection() 
{
  try 
  {
    sendMessage({type: 'candidate', label: '0', candidate: 'a=candidate:1927371098 1 udp 1694506751 127.0.0.1 55935 typ host generation 0'});
    pc = new webkitPeerConnection00(null, (function(){}));
    console.log("Created webkitPeerConnnection00");
  } catch (e) 
  {
    console.log("Failed to create PeerConnection, exception: " + e.message);
    alert("Cannot create PeerConnection object; Is the 'PeerConnection' flag enabled in about:flags?");
    return;
  }

  pc.onconnecting = function() { console.log("Session connecting"); }
  pc.onopen = function() { console.log("Session opened.");}
  pc.onaddstream = onRemoteStreamAdded;
  pc.onremovestream = function(event) { console.log("Remote stream removed")};
}

function onRemoteStreamAdded(event)
{
  console.log("Remote stream added.");
  var url = webkitURL.createObjectURL(event.stream);
  $("#remoteAudio").src = url;
}

function doCall() 
{
  console.log("Send offer to peer");
  var offer = pc.createOffer({audio:true});
  pc.setLocalDescription(pc.SDP_OFFER, offer);
  sendMessage({type: 'offer', sdp: offer.toSdp()});
  pc.startIce();
}

function sendMessage(message) 
{
  var msgString = JSON.stringify(message);
  console.log('C->S: ' + msgString);
  ws.send(msgString);
}

function processSignalingMessage(message) 
{
  console.log('S->C: ' + message);
  var msgObj = jQuery.parseJSON(message);
  console.log(msgObj.type);
  if (msgObj.type === 'answer') 
  {
    pc.setRemoteDescription(pc.SDP_ANSWER, new SessionDescription(msgObj.sdp));
  } 
  else if (msgObj.type === 'candidate') 
  {
    var candidateString = msgObj.candidate;
    var candidate = new IceCandidate(msgObj.label, candidateString);
    pc.processIceMessage(candidate);
  } 
  else if (msgObj.type === 'bye' && started) 
  {
    // onRemoteHangup();
  }
}
