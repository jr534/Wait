#include "wait_server.h"
#include "wait_client_session.h"
#include <QCoreApplication>
#include <QObject>
#include <QWebSocketServer>
#include <QWebSocket>
#include <QMap>
#include <QString>
#include <QList>
#include <QFile>
#include <QTextStream>

wait_Server::wait_Server(QObject *parent)
    : QObject{parent}
{

}


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

void wait_Server::add_timer_in_list(float segond)
{
    timer_list.append(segond);

}

void wait_Server::load_data()
{
    QFile fichier("../data/timer_list.txt");
    if (!fichier.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qDebug() << "Impossible d'ouvrir le fichier en lecture : " << fichier.errorString();
        return;
    }

    QTextStream flux(&fichier);

    while (!flux.atEnd()) {
        QString ligne = flux.readLine();
        float time=ligne.toFloat();
        timer_list.append(time);
    }
}

void wait_Server::New_Connection()
{
    QList<float>* p_timer_list = &timer_list;
    QWebSocket *pSocket = m_pserver->nextPendingConnection();

    if (pSocket){
        qDebug() << "nouvaux WAIT Client";
        m_pnewclient = new wait_Client_Session(pSocket,p_timer_list);

        // connect pour l'ajoute de temps dans la liste
        connect(m_pnewclient,&wait_Client_Session::signal_add_timer_data,this,&wait_Server::add_timer_in_list);

        User.append(m_pnewclient);
        qDebug() << "Le nouvaux est connecter";
    }
}



