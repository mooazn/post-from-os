package com.example.servermanagerapp;
import android.content.Intent;
import android.os.Bundle;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.jcraft.jsch.ChannelExec;
import com.jcraft.jsch.JSch;
import com.jcraft.jsch.Session;
import java.io.CharArrayWriter;
import java.io.InputStream;


public class sshActivity extends AppCompatActivity {

    TextView shellOutput;
    Session session;
    ChannelExec channel;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_ssh);
        shellOutput = findViewById(R.id.textView);

        Intent comingIntent = getIntent();
        ServerCredentials serverCredentials =
                (ServerCredentials) comingIntent.getSerializableExtra("serverCredentials");
        String host = serverCredentials.getHost();
        int port = Integer.parseInt(serverCredentials.getPort());
        String username = serverCredentials.getUsername();
        String password = serverCredentials.getPassword();

        Thread thread = new Thread(new Runnable() {
            @Override
            public void run() {
                try{
                    session = new JSch().getSession(username, host, port);
                    session.setPassword(password);
                    session.setConfig("StrictHostKeyChecking", "no");
                    session.connect();
                    if(session.isConnected()) {
                        channel = (ChannelExec) session.openChannel("exec");
                        channel.setCommand("ls");  // replace with own command
                        channel.connect();

                        InputStream input = channel.getInputStream();
                        int data = input.read();
                        CharArrayWriter outputBuffer = new CharArrayWriter();
                        while (data != -1) {
                            outputBuffer.append((char) data);
                            data = input.read();
                        }
                        shellOutput.setText(outputBuffer.toString());
                        channel.disconnect();
                    }
                    session.disconnect();
                }
                catch (Exception e){
                    System.out.println(e.getMessage());
                    e.printStackTrace();
                    if(!session.isConnected()) {
                        runOnUiThread(new Runnable() {
                            @Override
                            public void run() {
                                Toast.makeText(getApplicationContext(),
                                        "Cannot connect.", Toast.LENGTH_LONG).show();
                            }
                        });
                    }
                }
            }
        });
        thread.start();
    }
}
