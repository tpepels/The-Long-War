const ICE_CONFIG = {
  iceServers: [
    { urls: "stun:stun.cloudflare.com:3478" },
    { urls: "stun:stun.l.google.com:19302" },
  ],
};

function encodeDescription(description) {
  const bytes = new TextEncoder().encode(JSON.stringify({
    type: description.type,
    sdp: description.sdp,
  }));
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

function decodeDescription(token, expectedType) {
  const normalized = String(token || "").trim().replaceAll("-", "+").replaceAll("_", "/");
  if (!normalized) throw new Error("Connection token is empty.");
  const padding = "=".repeat((4 - normalized.length % 4) % 4);
  let binary;
  try {
    binary = atob(normalized + padding);
  } catch {
    throw new Error("Connection token is not valid.");
  }
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  let value;
  try {
    value = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    throw new Error("Connection token is not valid.");
  }
  if (!value || value.type !== expectedType || typeof value.sdp !== "string") {
    throw new Error("Connection token has the wrong type.");
  }
  return value;
}

function waitForIceGathering(peer, timeoutMs = 10000) {
  if (peer.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve, reject) => {
    let done = false;
    const finish = (error = null) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      peer.removeEventListener("icegatheringstatechange", changed);
      if (error) reject(error);
      else resolve();
    };
    const changed = () => {
      if (peer.iceGatheringState === "complete") finish();
    };
    const timer = setTimeout(() => finish(new Error(
      "Could not finish gathering network candidates. Try again, or use a different network."
    )), timeoutMs);
    peer.addEventListener("icegatheringstatechange", changed);
  });
}

function remoteEndpoint(peer, getChannel, onMessage, onState) {
  const emitState = () => {
    const channel = getChannel();
    onState?.({
      peer: peer.connectionState,
      channel: channel?.readyState || "none",
      connected: peer.connectionState === "connected" && channel?.readyState === "open",
    });
  };
  peer.addEventListener("connectionstatechange", emitState);
  peer.addEventListener("iceconnectionstatechange", emitState);

  return {
    send(payload) {
      const channel = getChannel();
      if (!channel || channel.readyState !== "open") {
        throw new Error("The remote player is not connected.");
      }
      channel.send(JSON.stringify(payload));
    },
    close() {
      const channel = getChannel();
      try { channel?.close(); } catch {}
      try { peer.close(); } catch {}
      emitState();
    },
    get connected() {
      const channel = getChannel();
      return peer.connectionState === "connected" && channel?.readyState === "open";
    },
  };
}

function configureChannel(channel, onMessage, onState) {
  channel.addEventListener("message", (event) => {
    try {
      onMessage?.(JSON.parse(event.data));
    } catch (error) {
      console.error("[remote] invalid message", error);
    }
  });
  channel.addEventListener("open", () => onState?.());
  channel.addEventListener("close", () => onState?.());
  channel.addEventListener("error", () => onState?.());
}

export async function createRemoteHost({ onMessage, onState } = {}) {
  if (typeof RTCPeerConnection === "undefined") {
    throw new Error("WebRTC is not available in this browser.");
  }
  const peer = new RTCPeerConnection(ICE_CONFIG);
  let channel = peer.createDataChannel("the-long-war", { ordered: true });
  const endpoint = remoteEndpoint(peer, () => channel, onMessage, onState);
  configureChannel(channel, onMessage, () => onState?.({
    peer: peer.connectionState,
    channel: channel.readyState,
    connected: endpoint.connected,
  }));

  const offer = await peer.createOffer();
  await peer.setLocalDescription(offer);
  await waitForIceGathering(peer);

  return {
    ...endpoint,
    inviteToken: encodeDescription(peer.localDescription),
    async acceptAnswer(token) {
      await peer.setRemoteDescription(decodeDescription(token, "answer"));
    },
  };
}

export async function createRemoteGuest(inviteToken, { onMessage, onState } = {}) {
  if (typeof RTCPeerConnection === "undefined") {
    throw new Error("WebRTC is not available in this browser.");
  }
  const peer = new RTCPeerConnection(ICE_CONFIG);
  let channel = null;
  const endpoint = remoteEndpoint(peer, () => channel, onMessage, onState);

  peer.addEventListener("datachannel", (event) => {
    channel = event.channel;
    configureChannel(channel, onMessage, () => onState?.({
      peer: peer.connectionState,
      channel: channel.readyState,
      connected: endpoint.connected,
    }));
  });

  await peer.setRemoteDescription(decodeDescription(inviteToken, "offer"));
  const answer = await peer.createAnswer();
  await peer.setLocalDescription(answer);
  await waitForIceGathering(peer);

  return {
    ...endpoint,
    answerToken: encodeDescription(peer.localDescription),
  };
}
