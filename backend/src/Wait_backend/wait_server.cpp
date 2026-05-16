#include "wait_server.h"
#include "wait_client_session.h"

#include <QObject>
#include <QWebSocketServer>
#include <QWebSocket>
#include <QMap>
#include <QString>
#include <QList>

wait_Server::wait_Server(QObject *parent)
    : QObject{parent}
{}


void wait_Server::start_waitServer(int porte)
{
    m_pserver = new QWebSocketServer(QStringLiteral("Wait"),QWebSocketServer::NonSecureMode);

    // C'est ici qu'on connecte le serveur à ton slot New_Connection
    connect(m_pserver, &QWebSocketServer::newConnection,this, &wait_Server::New_Connection);


    if (m_pserver->listen(QHostAddress::Any, porte)) {
        qDebug() << "WAIT Serveur start sur le port" << porte;
    }else{
        qDebug() << "Erreur: Le port" << porte << "est probablement en cours d'utilisation par un autre processus.";
    }
}

void wait_Server::New_Connection()
{
    QWebSocket *pSocket = m_pserver->nextPendingConnection();

    if (pSocket){
        qDebug() << "nouvaux WAIT Client";
        m_pnewclient = new wait_Client_Session(pSocket);


        User.append(m_pnewclient);
        qDebug() << "Le nouvaux est connecter";
    }
}



