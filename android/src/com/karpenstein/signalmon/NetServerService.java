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

   NetServerService.java: Android service that keeps running after the app is closed.
     Handles the PhoneStateListener events in the Android event system.
*/

package com.karpenstein.signalmon;

import android.app.IntentService;
import android.app.Service;
import android.os.IBinder;
import android.content.Intent;
import android.content.Context;
import android.util.Log;
import android.telephony.PhoneStateListener;
import android.telephony.TelephonyManager;
import android.telephony.SignalStrength;
import java.net.Socket;
import java.net.ServerSocket;
import java.io.IOException;
import java.util.ArrayList;
import org.json.JSONObject;
import org.json.JSONException;

/**
 * TODO: Make a properties page where you can set the port number
 */
public class NetServerService extends IntentService
//public class NetServerService extends Service
{
  private PhoneStateListener psListener;
  private TelephonyManager telephonyManager;
  private ArrayList<SignalStateListener> jsonStateListeners;
  private JSONObject jsonState;
  private NetServerThread server;
  
  public NetServerService()
  {
    super("NetServerService");
    jsonStateListeners = new ArrayList<SignalStateListener>();
  }
  
  public void addListener(SignalStateListener jsonStateListener)
  {
    Log.d("NetServerService", "Adding a listener for the signal state");
    jsonStateListeners.add(jsonStateListener);
  }

  private void notifyListeners()
  {
    Log.d("NetServerService","about to notify listeners, count = " + jsonStateListeners.size());
    for (SignalStateListener listener : jsonStateListeners)
    {
      listener.onStateChanged(jsonState);
    }
  }

  @Override
  public void onDestroy()
  {
    Log.d("NetServerService", "onDestroy happened to the NetServerService");
  }

  @Override
  public void onCreate()
  {
    super.onCreate();
    try 
    {
      jsonState = new JSONObject();
      jsonState.put("dataActivity", TelephonyManager.DATA_ACTIVITY_NONE);
    }
    catch (JSONException ex)
    {
      Log.d("NetServerService", "Failed to put data activity in the JSONObject");
    }

    // Get the telephony manager
    telephonyManager = (TelephonyManager) getSystemService(Context.TELEPHONY_SERVICE);
    if (telephonyManager == null)
      Log.d("NetServerService", "TelephonyManager was null.");
    Log.d("NetServerService", "about to create PhoneStateListener");
    // Create a new PhoneStateListener
    psListener = new PhoneStateListener() {
      @Override
      public void onDataActivity(int direction)
      {
        Log.d("NetServerService", "received onDataActivity message");
        try {
          jsonState.put("dataActivity", direction);
        }
        catch (JSONException ex)
        {}
        notifyListeners();
      }

      @Override
      public void onSignalStrengthsChanged(SignalStrength signalStrength)
      {
        Log.d("NetServerService", "received onSignalStrength message");
        try {
          jsonState.put("cdmaDbm", signalStrength.getCdmaDbm());
          jsonState.put("cdmaEcio", signalStrength.getCdmaEcio());
          jsonState.put("evdoDbm", signalStrength.getEvdoDbm());
          jsonState.put("evdoEcio", signalStrength.getEvdoEcio());
          jsonState.put("evdoSnr", signalStrength.getEvdoSnr());
          jsonState.put("gsmBitErrorRate", signalStrength.getGsmBitErrorRate());
          jsonState.put("gsmSignalStrength", signalStrength.getGsmSignalStrength());
          jsonState.put("isGsm", signalStrength.isGsm());
        }
        catch (JSONException ex)
        {}
        notifyListeners();
      }

      @Override
      public void onDataConnectionStateChanged(int state, int networkType)
      {
        Log.d("NetServerService", "received onDataConnectionStateChanged message");
        try 
        {
          jsonState.put("connState", state);
          jsonState.put("netType", networkType);
        }
        catch (JSONException ex)
        {}
        notifyListeners();
      }
    };
 
    Log.d("NetServerService", "about to call telephonyManager.listen");
    // Register the listener with the telephony manager
    telephonyManager.listen(psListener, PhoneStateListener.LISTEN_DATA_CONNECTION_STATE | 
                                        PhoneStateListener.LISTEN_SIGNAL_STRENGTHS |
                                        PhoneStateListener.LISTEN_DATA_ACTIVITY);
    Log.d("NetServerService", "done calling telephonyManager.listen -- exiting onCreate");
  }

  /*
  @Override
  public IBinder onBind(Intent intent)
  {
    return null;
  }
  */

  @Override
  public void onHandleIntent(Intent intent)
  //public int onStartCommand(Intent intent, int flags, int startId)
  {
    Log.d("NetServerService", "Starting onHandleIntent -- about to create serverthread");
    NetServerThread server = new NetServerThread(this);
    server.run();
    //return Service.START_STICKY;
  }
} 
