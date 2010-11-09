/*
   Copyright 2010 Nissim Karpenstein

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

   NetConnHandler.java: TCP Connection handler thread -- implements the protocol 
          and communicates with the clients
*/

package com.karpenstein.signalmon;

import android.content.Context;
import android.util.Log;
import android.os.Looper;
import java.net.Socket;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.PrintStream;
import java.io.DataInputStream;
import java.io.IOException;
import org.json.JSONObject;
import org.json.JSONException;

/**
 * Protocol: client throttles data by sending ticks (1 char 'G')
 * sends 'S' to disconnect.
 * on each receipt of the G, this sends the current state if it has changed, otherwise it sends {}.
 *
 * JSON Object:  dataActivity int
 *               connState int
 *               netType int
 *               cdmaDbm int
 *               cdmaEcio int
 *               evdoDbm int
 *               evdoEcio int
 *               evdoSnr int
 *               gsmBitErrorRate int
 *               gsmSignalStrenght int
 *               isGsm boolean
 */
public class NetConnHandler extends Thread implements SignalStateListener
{
 
  private Socket sock;
  private NetServerService server;
  private boolean stateChanged;
  private JSONObject state;
  private static final String nullObj = "{}";

  public NetConnHandler(Socket sock, NetServerService server)
  {
    super("NetConnHandler");
    this.sock = sock;
    this.server = server;
  }

  public void onStateChanged (JSONObject state)
  {
    stateChanged = true;
    this.state = state;
  }


  @Override
  public void run()
  {

    server.addListener(this);
    
    String line;
    try {
      Log.d("NetConnHandler", "about to create input and output streams");
      // Get input from the client
      DataInputStream in = new DataInputStream (sock.getInputStream());
      PrintStream out = new PrintStream(sock.getOutputStream());

      Log.d("NetConnHandler", "about to start looping");
      while((line = in.readLine()) != null && line.equals("G")) {
        if (stateChanged)
        {
          stateChanged = false;
          out.println(state.toString());
        }
        else
          out.println(nullObj);
      }

      sock.close();
    } catch (IOException ioe) {
      Log.e("SignalMonitor.NetConnHandler", "IOException on socket r/w: " + ioe, ioe);
    }

  }
} 
