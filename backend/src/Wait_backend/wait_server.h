#ifndef WAIT_SERVER_H
#define WAIT_SERVER_H

#include <QObject>
#include <QObject>
#include <QWebSocketServer>
#include <QWebSocket>
#include <QMap>
#include <QString>
#include <QList>
#include "wait_client_session.h"

class wait_Server : public QObject
{
    Q_OBJECT
public:
    explicit wait_Server(QObject *parent = nullptr);
    void start_waitServer (int porte);
private:

    QWebSocketServer *m_pserver;
    wait_Client_Session *m_pnewclient;
    int porte;
    QList<wait_Client_Session*> User;
    QList<float> timer_list;
    void add_timer_in_list(float segond);
    void load_data()

private slots:
    void New_Connection();
signals:
};

#endif // WAIT_SERVER_H
