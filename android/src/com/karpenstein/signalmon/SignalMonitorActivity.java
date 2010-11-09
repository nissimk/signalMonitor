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

   SignalMonitorActivity.java: Main Activity Class fot the Signal Monitor Server App
*/

package com.karpenstein.signalmon;

import android.app.Activity;
import android.os.Bundle;
import android.content.Context;
import android.content.Intent;
import android.telephony.PhoneStateListener;
import android.telephony.TelephonyManager;
import android.telephony.SignalStrength;
import android.widget.TextView;
import android.util.Log;
import org.json.JSONObject;
import org.json.JSONException;

/**
 * TODO: create a data structure that holds all of the signal strength and Data state info
 *         Create an IntentService to start the server.
 *         Server should listen for clients
 *         When client connects, server should spawn a thread.
 *         client will send one line with R for Ready.
 *         service thread should register PhoneStateListener that writes a JSON object to the socket
 *         service thread should go into sleep loop waking up every so often to send keep alive message
 *         service thread should register listener to handle an event that tells it to shut off
 *         service thread should know that client disconnected and shutdown.
 */
public class SignalMonitorActivity extends Activity
{
  TextView textOut;
  TelephonyManager telephonyManager;
  PhoneStateListener listener;

  /** Called when the activity is first created. */
  @Override
  public void onCreate(Bundle savedInstanceState)
  {
    super.onCreate(savedInstanceState);
    setContentView(R.layout.main);

    // Get the UI
    textOut = (TextView) findViewById(R.id.textOut);

    // Get the telephony manager
    telephonyManager = (TelephonyManager) getSystemService(Context.TELEPHONY_SERVICE);

    // Create a new PhoneStateListener
    listener = new PhoneStateListener() {
      @Override
      public void onDataActivity(int direction)
      {
        String dirString = "N/A";
        switch (direction) {
          case TelephonyManager.DATA_ACTIVITY_NONE:
            dirString = "DATA_ACTIVITY_NONE";
            break;
          case TelephonyManager.DATA_ACTIVITY_IN:
            dirString = "DATA_ACTIVITY_IN";
            break;
          case TelephonyManager.DATA_ACTIVITY_OUT:
            dirString = "DATA_ACTIVITY_OUT";
            break;
          case TelephonyManager.DATA_ACTIVITY_INOUT:
            dirString = "DATA_ACTIVITY_INOUT";
            break;
          case TelephonyManager.DATA_ACTIVITY_DORMANT:
            dirString = "DATA_ACTIVITY_DORMANT";
            break;
        }
        textOut.append(dirString + "\n");
      }

      @Override
      public void onSignalStrengthsChanged(SignalStrength signalStrength)
      {
        textOut.append(signalStrength.toString() + "\n");
      }

      @Override
      public void onDataConnectionStateChanged(int state, int networkType)
      {
        String stateString = "N/A";
        String netTypString = "N/A";
        switch (state) {
          case TelephonyManager.DATA_CONNECTED:
            stateString = "DATA_CONNECTED";
            break;
          case TelephonyManager.DATA_CONNECTING:
            stateString = "DATA_CONNECTING";
            break;
          case TelephonyManager.DATA_DISCONNECTED:
            stateString = "DATA_DISCONNECTED";
            break;
          case TelephonyManager.DATA_SUSPENDED:
            stateString = "DATA_SUSPENDED";
            break;
        }
        switch (networkType) {
          case TelephonyManager.NETWORK_TYPE_1xRTT:
            netTypString = "NETWORK_TYPE_1xRTT";
            break;
          case TelephonyManager.NETWORK_TYPE_CDMA:
            netTypString = "NETWORK_TYPE_CDMA";
            break;
          case TelephonyManager.NETWORK_TYPE_EDGE:
            netTypString = "NETWORK_TYPE_EDGE";
            break;
          case TelephonyManager.NETWORK_TYPE_EVDO_0:
            netTypString = "NETWORK_TYPE_EVDO_0";
            break;
          case TelephonyManager.NETWORK_TYPE_EVDO_A:
            netTypString = "NETWORK_TYPE_EVDO_A";
            break;
          case TelephonyManager.NETWORK_TYPE_GPRS:
            netTypString = "NETWORK_TYPE_GPRS";
            break;
          case TelephonyManager.NETWORK_TYPE_HSDPA:
            netTypString = "NETWORK_TYPE_HSDPA";
            break;
          case TelephonyManager.NETWORK_TYPE_HSPA:
            netTypString = "NETWORK_TYPE_HSPA";
            break;
          case TelephonyManager.NETWORK_TYPE_HSUPA:
            netTypString = "NETWORK_TYPE_HSUPA";
            break;
          case TelephonyManager.NETWORK_TYPE_IDEN:
            netTypString = "NETWORK_TYPE_IDE";
            break;
          case TelephonyManager.NETWORK_TYPE_UMTS:
            netTypString = "NETWORK_TYPE_UMTS";
            break;
          case TelephonyManager.NETWORK_TYPE_UNKNOWN:
            netTypString = "NETWORK_TYPE_UNKNOWN";
            break;
        }
        textOut.append(String.format("onDataConnectionStateChanged: %s; %s\n", stateString, netTypString));
      }
    };
 
    // Register the listener with the telephony manager
    telephonyManager.listen(listener, PhoneStateListener.LISTEN_DATA_CONNECTION_STATE | 
                                      PhoneStateListener.LISTEN_SIGNAL_STRENGTHS |
                                      PhoneStateListener.LISTEN_DATA_ACTIVITY);

    // start the NetServerService
    startService(new Intent(this, NetServerService.class));
  }
}
