package com.example.servermanagerapp;
import java.io.Serializable;

public class ServerCredentials implements Serializable {

    private final String host;
    private final String port;
    private final String username;
    private final String password;

    ServerCredentials(String host, String port, String username, String password){
        this.host = host;
        this.port = port;
        this.username = username;
        this.password = password;
    }

    public String getHost() {
        return host;
    }

    public String getPort() {
        return port;
    }


    public String getUsername() {
        return username;
    }


    public String getPassword() {
        return password;
    }

}
